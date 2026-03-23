import asyncio
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import apple_music
import classifier
from apple_music import AppleMusicNotRunningError
from models import ClassifyRequest, ControlRequest, CustomPlayRequest, SeekRequest, VolumeRequest
from player import state


async def monitor_playback():
    prev_near_end = False
    while state.is_monitoring:
        try:
            ps = apple_music.get_player_state()
            near_end = ps["duration"] > 0 and ps["position"] >= ps["duration"] - 2
            is_stopped = ps["state"] in ("paused", "stopped")
            if prev_near_end and is_stopped and state.queue:
                track = state.next()
                if track and track.playlist_name:
                    apple_music.play_track(track.playlist_name, track.database_id)
            prev_near_end = near_end
        except Exception:
            pass
        await asyncio.sleep(1)


def _ensure_monitoring():
    if not state.is_monitoring:
        state.is_monitoring = True
        asyncio.create_task(monitor_playback())


def _play_track(track):
    apple_music.play_track(track.playlist_name, track.database_id)
    _ensure_monitoring()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    state.is_monitoring = False


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppleMusicNotRunningError)
async def apple_music_error_handler(request, exc):
    return JSONResponse(status_code=503, content={"detail": "Apple Music is not running. Please open Apple Music."})


# --- Health ---


@app.get("/api/health")
def health():
    return {"connected": apple_music.is_running()}


# --- Playlists ---


@app.get("/api/playlists")
def list_playlists():
    return {"playlists": apple_music.get_playlists()}


# --- Classification ---


@app.post("/api/classify")
async def classify(req: ClassifyRequest):
    if state.classify_status == "classifying":
        return {"status": "classifying", "progress": state.classify_progress}
    state.classify_status = "classifying"
    state.classify_progress = ""
    state.playlist_names = req.playlists

    async def run_classification():
        try:
            all_tracks = []
            for pl in req.playlists:
                all_tracks.extend(apple_music.get_tracks(pl))

            state.all_tracks = all_tracks

            def on_progress(p: str):
                state.classify_progress = p

            loop = asyncio.get_event_loop()
            categories = await loop.run_in_executor(
                None, lambda: classifier.classify_tracks(all_tracks, on_progress)
            )
            state.categories = categories
            state.classify_status = "done"
        except Exception as e:
            state.classify_status = "error"
            state.classify_progress = str(e)

    asyncio.create_task(run_classification())
    return {"status": "classifying"}


@app.get("/api/classify/status")
def classify_status():
    return {"status": state.classify_status, "progress": state.classify_progress}


# --- Categories ---


@app.get("/api/categories")
def get_categories():
    return {
        "playlist_names": state.playlist_names,
        "categories": {
            name: [t.model_dump(include={"database_id", "name", "artist", "album", "duration"}) for t in tracks]
            for name, tracks in state.categories.items()
        },
    }


# --- Playback ---


@app.post("/api/play/category/{name:path}")
async def play_category(name: str):
    track = state.start_category(name)
    if not track:
        raise HTTPException(400, f"Category '{name}' is empty or not found")
    _play_track(track)
    return {"playing": track.name, "artist": track.artist}


@app.post("/api/play/custom")
async def play_custom(req: CustomPlayRequest):
    if not state.all_tracks:
        raise HTTPException(400, "No tracks available. Classify a playlist first.")
    loop = asyncio.get_event_loop()
    matched = await loop.run_in_executor(
        None, lambda: classifier.pick_by_description(req.description, state.all_tracks)
    )
    if not matched:
        raise HTTPException(400, "No tracks match this description")
    track = state.start_custom(matched)
    _play_track(track)
    return {"playing": track.name, "artist": track.artist, "matched_count": len(matched)}


# --- Player controls ---


@app.post("/api/player/control")
def player_control(req: ControlRequest):
    if req.action == "pause":
        apple_music.pause()
    elif req.action == "resume":
        apple_music.resume()
    elif req.action == "next":
        track = state.next()
        if track and track.playlist_name:
            apple_music.play_track(track.playlist_name, track.database_id)
    elif req.action == "prev":
        track = state.prev()
        if track and track.playlist_name:
            apple_music.play_track(track.playlist_name, track.database_id)
        else:
            apple_music.set_position(0)
    else:
        raise HTTPException(400, f"Unknown action: {req.action}")
    return {"ok": True}


@app.get("/api/player/status")
def player_status():
    try:
        ps = apple_music.get_player_state()
        vol = apple_music.get_volume()
        return {
            **ps,
            "volume": vol,
            "category": state.current_category,
            "queue_length": len(state.queue),
            "queue_index": state.current_index,
        }
    except AppleMusicNotRunningError:
        return {"state": "disconnected", "name": "", "artist": "", "position": 0, "duration": 0, "volume": 0}


@app.get("/api/player/artwork")
def player_artwork():
    data = apple_music.get_artwork()
    if not data:
        raise HTTPException(404, "No artwork available")
    content_type = "image/png" if data[:4] == b'\x89PNG' else "image/jpeg"
    return Response(content=data, media_type=content_type)


@app.post("/api/player/volume")
def player_volume(req: VolumeRequest):
    apple_music.set_volume(req.volume)
    return {"volume": req.volume}


@app.post("/api/player/seek")
def player_seek(req: SeekRequest):
    apple_music.set_position(req.position)
    return {"position": req.position}


@app.post("/api/player/jump/{index}")
async def player_jump(index: int):
    if index < 0 or index >= len(state.queue):
        raise HTTPException(400, "Invalid queue index")
    state.current_index = index
    track = state.queue[index]
    _play_track(track)
    return {"playing": track.name, "artist": track.artist}


@app.get("/api/player/queue")
def player_queue():
    return {
        "queue": [
            t.model_dump(include={"database_id", "name", "artist", "duration"})
            for t in state.queue
        ],
        "current_index": state.current_index,
    }


@app.delete("/api/player/queue/{index}")
def remove_from_queue(index: int):
    next_track = state.remove_from_queue(index)
    if next_track and next_track.playlist_name:
        apple_music.play_track(next_track.playlist_name, next_track.database_id)
    return {"ok": True}
