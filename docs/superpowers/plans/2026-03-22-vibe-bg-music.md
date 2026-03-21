# Vibe BG Music Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python+Next.js app that controls Apple Music via osascript, classifies playlist tracks with GPT, and provides a WebUI for category-based playback.

**Architecture:** FastAPI backend (port 8000) wraps osascript for Apple Music control and OpenAI SDK for classification. Next.js frontend (port 3000, Bun) polls backend every 1s for player state. No database — all state in memory.

**Tech Stack:** Python 3.12+ / FastAPI / uvicorn / openai SDK / python-dotenv (uv) | Next.js 15 / TypeScript / Tailwind CSS / swr (Bun)

**Spec:** `docs/superpowers/specs/2026-03-22-vibe-bg-music-design.md`

---

## File Map

### Backend (`backend/`)

| File | Responsibility |
|------|---------------|
| `pyproject.toml` | Project metadata and dependencies |
| `apple_music.py` | osascript wrapper: all Apple Music interactions |
| `classifier.py` | OpenAI classification + custom description matching |
| `player.py` | PlayerState, queue management, auto-continuation |
| `main.py` | FastAPI app, routes, CORS, background tasks |

### Frontend (`frontend/`)

| File | Responsibility |
|------|---------------|
| `package.json` | Dependencies |
| `tailwind.config.ts` | Tailwind config (default from create-next-app, no custom changes needed — design tokens live in CSS variables) |
| `src/app/layout.tsx` | Root layout, Geist font, global providers |
| `src/app/page.tsx` | Main page composing all components |
| `src/app/globals.css` | Tailwind directives + CSS custom properties |
| `src/lib/api.ts` | Backend API client (fetch wrappers) |
| `src/components/Navbar.tsx` | Sticky nav with connection status |
| `src/components/PlaylistGrid.tsx` | Playlist selection grid + classify button |
| `src/components/CategoryGrid.tsx` | Category cards + CustomPickCard + filler cards |
| `src/components/PlayerBar.tsx` | Bottom player bar with controls |
| `src/components/QueuePanel.tsx` | Queue panel with minimize |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `backend/pyproject.toml`
- Create: `.env`
- Create: `.gitignore`

- [ ] **Step 1: Create backend project with uv**

```bash
cd /Users/mitsuha/vibe-bg-music
uv init backend --python 3.12
```

- [ ] **Step 2: Add backend dependencies**

```bash
cd /Users/mitsuha/vibe-bg-music/backend
uv add fastapi uvicorn openai python-dotenv
```

- [ ] **Step 3: Create .env file**

Create `/Users/mitsuha/vibe-bg-music/.env`:
```env
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
GPT_LANGUAGE=en
```

- [ ] **Step 4: Create .gitignore**

Create `/Users/mitsuha/vibe-bg-music/.gitignore`:
```
.env
__pycache__/
.venv/
node_modules/
.next/
*.pyc
.DS_Store
```

- [ ] **Step 5: Scaffold frontend with Bun + Next.js**

```bash
cd /Users/mitsuha/vibe-bg-music
bunx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --no-import-alias --use-bun
```

- [ ] **Step 6: Add frontend dependencies**

```bash
cd /Users/mitsuha/vibe-bg-music/frontend
bun add swr
```

- [ ] **Step 7: Commit**

```bash
cd /Users/mitsuha/vibe-bg-music
git add -A
git commit -m "chore: scaffold backend (uv/FastAPI) and frontend (Bun/Next.js)"
```

---

## Task 2: Apple Music osascript Wrapper

**Files:**
- Create: `backend/apple_music.py`

- [ ] **Step 1: Implement apple_music.py**

```python
import subprocess
import json


class AppleMusicNotRunningError(Exception):
    pass


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _run(script: str) -> str:
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        error = result.stderr.strip()
        if "not running" in error.lower() or "(-600)" in error:
            raise AppleMusicNotRunningError("Apple Music is not running")
        raise RuntimeError(f"osascript error: {error}")
    return result.stdout.strip()


def is_running() -> bool:
    script = 'tell application "System Events" to (name of processes) contains "Music"'
    return _run(script) == "true"


def _ensure_running():
    if not is_running():
        raise AppleMusicNotRunningError("Apple Music is not running")


def get_playlists() -> list[dict]:
    _ensure_running()
    script = '''
    tell application "Music"
        set output to ""
        repeat with p in user playlists
            set pName to name of p
            set pCount to count of tracks of p
            set output to output & pName & "|||" & pCount & "\\n"
        end repeat
        return output
    end tell
    '''
    raw = _run(script)
    playlists = []
    for line in raw.strip().split("\n"):
        if "|||" not in line:
            continue
        parts = line.split("|||")
        playlists.append({"name": parts[0], "track_count": int(parts[1])})
    return playlists


def get_tracks(playlist_name: str) -> list[dict]:
    _ensure_running()
    safe_name = _escape(playlist_name)
    script = f'''
    tell application "Music"
        set output to ""
        set theTracks to tracks of user playlist "{safe_name}"
        repeat with t in theTracks
            set tName to name of t
            set tArtist to artist of t
            set tAlbum to album of t
            set tDuration to duration of t
            set tID to database ID of t
            set output to output & tID & "|||" & tName & "|||" & tArtist & "|||" & tAlbum & "|||" & tDuration & "\\n"
        end repeat
        return output
    end tell
    '''
    raw = _run(script)
    tracks = []
    for line in raw.strip().split("\n"):
        if "|||" not in line:
            continue
        parts = line.split("|||")
        if len(parts) < 5:
            continue
        tracks.append({
            "database_id": int(parts[0]),
            "name": parts[1],
            "artist": parts[2],
            "album": parts[3],
            "duration": float(parts[4]),
        })
    return tracks


def play_track(playlist_name: str, database_id: int):
    _ensure_running()
    safe_name = _escape(playlist_name)
    script = f'''
    tell application "Music"
        set theTracks to (every track of user playlist "{safe_name}" whose database ID is {database_id})
        if (count of theTracks) > 0 then
            play item 1 of theTracks
        end if
    end tell
    '''
    _run(script)


def pause():
    _ensure_running()
    _run('tell application "Music" to pause')


def resume():
    _ensure_running()
    _run('tell application "Music" to play')


def next_track():
    _ensure_running()
    _run('tell application "Music" to next track')


def prev_track():
    _ensure_running()
    _run('tell application "Music" to previous track')


def get_player_state() -> dict:
    _ensure_running()
    script = '''
    tell application "Music"
        set pState to player state as string
        if pState is "stopped" then
            return "stopped|||||||0|||0|||stopped"
        end if
        set tName to name of current track
        set tArtist to artist of current track
        set tID to database ID of current track
        set tPos to player position
        set tDur to duration of current track
        return tName & "|||" & tArtist & "|||" & tID & "|||" & tPos & "|||" & tDur & "|||" & pState
    end tell
    '''
    raw = _run(script)
    parts = raw.split("|||")
    if len(parts) < 6:
        return {"name": "", "artist": "", "database_id": 0, "position": 0, "duration": 0, "state": "stopped"}
    return {
        "name": parts[0],
        "artist": parts[1],
        "database_id": int(parts[2]) if parts[2] else 0,
        "position": float(parts[3]) if parts[3] else 0,
        "duration": float(parts[4]) if parts[4] else 0,
        "state": parts[5].strip(),
    }


def set_position(seconds: float):
    _ensure_running()
    _run(f'tell application "Music" to set player position to {seconds}')


def get_volume() -> int:
    _ensure_running()
    return int(_run('tell application "Music" to get sound volume'))


def set_volume(level: int):
    _ensure_running()
    level = max(0, min(100, level))
    _run(f'tell application "Music" to set sound volume to {level}')
```

- [ ] **Step 2: Manual smoke test**

```bash
cd /Users/mitsuha/vibe-bg-music/backend
uv run python -c "import apple_music; print(apple_music.is_running())"
```

Expected: `True` (if Apple Music is open) or `False`.

- [ ] **Step 3: Commit**

```bash
git add backend/apple_music.py
git commit -m "feat: add Apple Music osascript wrapper"
```

---

## Task 3: GPT Classifier

**Files:**
- Create: `backend/classifier.py`

- [ ] **Step 1: Implement classifier.py**

```python
import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
)
_language = os.getenv("GPT_LANGUAGE", "en")

BATCH_SIZE = 50


def _classify_batch(
    tracks: list[dict],
    existing_categories: list[str] | None = None,
) -> dict[str, list[dict]]:
    track_info = "\n".join(
        f"- [{t['database_id']}] {t['name']} — {t['artist']} ({t['album']})"
        for t in tracks
    )

    category_hint = ""
    if existing_categories:
        category_hint = (
            f"\nUse these existing category names when possible: {', '.join(existing_categories)}. "
            "You may add new categories if needed."
        )

    prompt = f"""Classify the following music tracks into genre categories.
Decide the appropriate granularity yourself (e.g., "Indie Rock", "Synthwave", "Lo-fi Hip Hop").
Output all category names in {_language}.{category_hint}

Tracks:
{track_info}

Return ONLY valid JSON in this format:
{{"categories": {{"CategoryName": [{{"name": "...", "artist": "...", "database_id": 12345}}, ...]}}}}
"""

    for attempt in range(3):
        try:
            response = _client.responses.create(
                model="gpt-4.1-mini",
                input=prompt,
            )
            text = response.output_text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            data = json.loads(text)
            return data.get("categories", {})
        except (json.JSONDecodeError, KeyError, AttributeError):
            if attempt == 2:
                return {}
    return {}


def classify_tracks(
    tracks: list[dict],
    progress_callback=None,
) -> dict[str, list[dict]]:
    if len(tracks) <= BATCH_SIZE:
        if progress_callback:
            progress_callback("1/1 batches")
        return _classify_batch(tracks)

    batches = [tracks[i:i + BATCH_SIZE] for i in range(0, len(tracks), BATCH_SIZE)]
    total = len(batches)
    all_categories: dict[str, list[dict]] = {}
    existing_names: list[str] = []

    for idx, batch in enumerate(batches):
        if progress_callback:
            progress_callback(f"{idx + 1}/{total} batches")
        result = _classify_batch(batch, existing_names if existing_names else None)
        for cat_name, cat_tracks in result.items():
            if cat_name not in all_categories:
                all_categories[cat_name] = []
                existing_names.append(cat_name)
            all_categories[cat_name].extend(cat_tracks)

    # Validate: collect classified IDs
    classified_ids = set()
    valid_ids = {t["database_id"] for t in tracks}
    for cat_tracks in all_categories.values():
        cat_tracks[:] = [t for t in cat_tracks if t.get("database_id") in valid_ids]
        classified_ids.update(t["database_id"] for t in cat_tracks)

    # Uncategorized fallback
    uncategorized = [t for t in tracks if t["database_id"] not in classified_ids]
    if uncategorized:
        label = {"zh-CN": "未分类", "ja": "未分類"}.get(_language, "Uncategorized")
        all_categories[label] = uncategorized

    return all_categories


def pick_by_description(description: str, tracks: list[dict]) -> list[dict]:
    track_info = "\n".join(
        f"- [{t['database_id']}] {t['name']} — {t['artist']} ({t['album']})"
        for t in tracks
    )
    prompt = f"""From the following music tracks, select the ones that match this description: "{description}"

Tracks:
{track_info}

Return ONLY valid JSON: {{"track_ids": [12345, 67890, ...]}}
If no tracks match, return {{"track_ids": []}}
"""
    try:
        response = _client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
        )
        text = response.output_text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        data = json.loads(text)
        valid_ids = {t["database_id"] for t in tracks}
        matched_ids = set(data.get("track_ids", [])) & valid_ids
        return [t for t in tracks if t["database_id"] in matched_ids]
    except (json.JSONDecodeError, KeyError, AttributeError):
        return []
```

- [ ] **Step 2: Commit**

```bash
git add backend/classifier.py
git commit -m "feat: add GPT classifier with batch support and custom description matching"
```

---

## Task 4: Player State Manager

**Files:**
- Create: `backend/player.py`

- [ ] **Step 1: Implement player.py**

```python
import random
import asyncio
from dataclasses import dataclass, field


@dataclass
class Track:
    database_id: int
    name: str
    artist: str
    album: str
    duration: float


@dataclass
class PlayerState:
    playlist_name: str | None = None
    categories: dict[str, list[Track]] = field(default_factory=dict)
    current_category: str | None = None
    queue: list[Track] = field(default_factory=list)
    current_index: int = 0
    is_monitoring: bool = False
    classify_status: str = "idle"  # idle | classifying | done | error
    classify_progress: str = ""
    _all_tracks: list[dict] = field(default_factory=list)

    def set_categories(self, categories: dict[str, list[dict]]):
        self.categories = {}
        for name, tracks in categories.items():
            self.categories[name] = [
                Track(
                    database_id=t["database_id"],
                    name=t["name"],
                    artist=t["artist"],
                    album=t.get("album", ""),
                    duration=t.get("duration", 0),
                )
                for t in tracks
            ]

    def start_category(self, category_name: str) -> Track | None:
        if category_name not in self.categories:
            return None
        tracks = self.categories[category_name]
        if not tracks:
            return None
        self.current_category = category_name
        self.queue = list(tracks)
        random.shuffle(self.queue)
        self.current_index = 0
        return self.queue[0]

    def start_custom(self, tracks: list[Track]) -> Track | None:
        if not tracks:
            return None
        self.current_category = "__custom__"
        self.queue = list(tracks)
        random.shuffle(self.queue)
        self.current_index = 0
        return self.queue[0]

    def next(self) -> Track | None:
        if not self.queue:
            return None
        self.current_index += 1
        if self.current_index >= len(self.queue):
            random.shuffle(self.queue)
            self.current_index = 0
        return self.queue[self.current_index]

    def prev(self) -> Track | None:
        if not self.queue:
            return None
        if self.current_index > 0:
            self.current_index -= 1
        return self.queue[self.current_index]

    def remove_from_queue(self, index: int) -> Track | None:
        if index < 0 or index >= len(self.queue):
            return None
        is_current = index == self.current_index
        self.queue.pop(index)
        if not self.queue:
            if self.current_category and self.current_category in self.categories:
                return self.start_category(self.current_category)
            return None
        if is_current:
            if self.current_index >= len(self.queue):
                self.current_index = 0
            return self.queue[self.current_index]
        elif index < self.current_index:
            self.current_index -= 1
        return None

    def current_track(self) -> Track | None:
        if not self.queue or self.current_index >= len(self.queue):
            return None
        return self.queue[self.current_index]

    def get_all_tracks_flat(self) -> list[dict]:
        return self._all_tracks


state = PlayerState()
```

- [ ] **Step 2: Commit**

```bash
git add backend/player.py
git commit -m "feat: add PlayerState manager with queue and auto-continuation logic"
```

---

## Task 5: FastAPI Application

**Files:**
- Create: `backend/main.py`

- [ ] **Step 1: Implement main.py**

```python
import asyncio
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import apple_music
from apple_music import AppleMusicNotRunningError
import classifier
from player import state, Track


# --- Background monitor ---

async def monitor_playback():
    prev_near_end = False
    while state.is_monitoring:
        try:
            ps = apple_music.get_player_state()
            near_end = ps["duration"] > 0 and ps["position"] >= ps["duration"] - 2
            is_stopped = ps["state"] in ("paused", "stopped")

            if prev_near_end and is_stopped and state.queue:
                track = state.next()
                if track and state.playlist_name:
                    apple_music.play_track(state.playlist_name, track.database_id)

            prev_near_end = near_end
        except Exception:
            pass
        await asyncio.sleep(1)


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


# --- Models ---

class ClassifyRequest(BaseModel):
    playlist: str

class ControlRequest(BaseModel):
    action: str  # pause | resume | next | prev

class VolumeRequest(BaseModel):
    volume: int

class SeekRequest(BaseModel):
    position: float

class CustomPlayRequest(BaseModel):
    description: str


# --- Exception handler ---

@app.exception_handler(AppleMusicNotRunningError)
async def apple_music_error_handler(request, exc):
    return JSONResponse(status_code=503, content={"detail": "Apple Music is not running. Please open Apple Music."})


# --- Routes ---

@app.get("/api/health")
def health():
    return {"connected": apple_music.is_running()}


@app.get("/api/playlists")
def list_playlists():
    try:
        return {"playlists": apple_music.get_playlists()}
    except AppleMusicNotRunningError:
        raise HTTPException(503, "Apple Music is not running")


@app.post("/api/classify")
async def classify(req: ClassifyRequest):
    if state.classify_status == "classifying":
        return {"status": "classifying", "progress": state.classify_progress}

    state.classify_status = "classifying"
    state.classify_progress = ""
    state.playlist_name = req.playlist

    async def run_classification():
        try:
            tracks = apple_music.get_tracks(req.playlist)
            state._all_tracks = tracks

            def on_progress(p: str):
                state.classify_progress = p

            loop = asyncio.get_event_loop()
            categories = await loop.run_in_executor(
                None, lambda: classifier.classify_tracks(tracks, on_progress)
            )
            state.set_categories(categories)
            state.classify_status = "done"
        except Exception as e:
            state.classify_status = "error"
            state.classify_progress = str(e)

    asyncio.create_task(run_classification())
    return {"status": "classifying"}


@app.get("/api/classify/status")
def classify_status():
    return {
        "status": state.classify_status,
        "progress": state.classify_progress,
    }


@app.get("/api/categories")
def get_categories():
    return {
        "playlist_name": state.playlist_name,
        "categories": {
            name: [{"database_id": t.database_id, "name": t.name, "artist": t.artist, "album": t.album, "duration": t.duration} for t in tracks]
            for name, tracks in state.categories.items()
        }
    }


@app.post("/api/play/category/{name}")
def play_category(name: str):
    track = state.start_category(name)
    if not track:
        raise HTTPException(400, f"Category '{name}' is empty or not found")
    try:
        apple_music.play_track(state.playlist_name, track.database_id)
    except AppleMusicNotRunningError:
        raise HTTPException(503, "Apple Music is not running")

    if not state.is_monitoring:
        state.is_monitoring = True
        asyncio.create_task(monitor_playback())

    return {"playing": track.name, "artist": track.artist}


@app.post("/api/play/custom")
async def play_custom(req: CustomPlayRequest):
    all_tracks = state.get_all_tracks_flat()
    if not all_tracks:
        raise HTTPException(400, "No tracks available. Classify a playlist first.")

    loop = asyncio.get_event_loop()
    matched = await loop.run_in_executor(
        None, lambda: classifier.pick_by_description(req.description, all_tracks)
    )
    if not matched:
        raise HTTPException(400, "No tracks match this description")

    matched_as_tracks = [
        Track(database_id=t["database_id"], name=t["name"], artist=t["artist"], album=t.get("album", ""), duration=t.get("duration", 0))
        for t in matched
    ]
    track = state.start_custom(matched_as_tracks)
    try:
        apple_music.play_track(state.playlist_name, track.database_id)
    except AppleMusicNotRunningError:
        raise HTTPException(503, "Apple Music is not running")

    if not state.is_monitoring:
        state.is_monitoring = True
        asyncio.create_task(monitor_playback())

    return {"playing": track.name, "artist": track.artist, "matched_count": len(matched)}


@app.post("/api/player/control")
def player_control(req: ControlRequest):
    try:
        if req.action == "pause":
            apple_music.pause()
        elif req.action == "resume":
            apple_music.resume()
        elif req.action == "next":
            track = state.next()
            if track and state.playlist_name:
                apple_music.play_track(state.playlist_name, track.database_id)
        elif req.action == "prev":
            track = state.prev()
            if track and state.playlist_name:
                apple_music.play_track(state.playlist_name, track.database_id)
            else:
                apple_music.set_position(0)
        else:
            raise HTTPException(400, f"Unknown action: {req.action}")
    except AppleMusicNotRunningError:
        raise HTTPException(503, "Apple Music is not running")
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


@app.post("/api/player/volume")
def player_volume(req: VolumeRequest):
    try:
        apple_music.set_volume(req.volume)
    except AppleMusicNotRunningError:
        raise HTTPException(503, "Apple Music is not running")
    return {"volume": req.volume}


@app.post("/api/player/seek")
def player_seek(req: SeekRequest):
    try:
        apple_music.set_position(req.position)
    except AppleMusicNotRunningError:
        raise HTTPException(503, "Apple Music is not running")
    return {"position": req.position}


@app.get("/api/player/queue")
def player_queue():
    return {
        "queue": [
            {"database_id": t.database_id, "name": t.name, "artist": t.artist, "duration": t.duration}
            for t in state.queue
        ],
        "current_index": state.current_index,
    }


@app.delete("/api/player/queue/{index}")
def remove_from_queue(index: int):
    next_track = state.remove_from_queue(index)
    if next_track and state.playlist_name:
        try:
            apple_music.play_track(state.playlist_name, next_track.database_id)
        except AppleMusicNotRunningError:
            raise HTTPException(503, "Apple Music is not running")
    return {"ok": True}
```

- [ ] **Step 2: Test backend starts**

```bash
cd /Users/mitsuha/vibe-bg-music/backend
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

Verify: open `http://localhost:8000/api/health` returns JSON.

- [ ] **Step 3: Commit**

```bash
git add backend/main.py
git commit -m "feat: add FastAPI app with all API routes"
```

---

## Task 6: Frontend Foundation (Layout, Globals, API Client)

**Files:**
- Modify: `frontend/src/app/layout.tsx`
- Modify: `frontend/src/app/globals.css`
- Create: `frontend/src/lib/api.ts`

- [ ] **Step 1: Update globals.css with nextjs.org design tokens**

Replace `frontend/src/app/globals.css` with:
```css
@import "tailwindcss";

:root {
  --ds-background-100: #000;
  --ds-background-200: #0a0a0a;
  --ds-gray-100: #111;
  --ds-gray-200: #1a1a1a;
  --ds-gray-400: rgba(255,255,255,0.12);
  --ds-gray-700: #666;
  --ds-gray-900: #888;
  --ds-gray-1000: #ededed;
  --ds-gray-alpha-200: rgba(255,255,255,0.06);
  --ds-gray-alpha-400: rgba(255,255,255,0.1);
  --geist-foreground: #ededed;
  --geist-background: #000;
  --accents-2: #333;
  --accents-3: #444;
  --geist-radius: 8px;
  --transition-duration: 150ms;
}

body {
  background: var(--ds-background-100);
  color: var(--ds-gray-1000);
  -webkit-font-smoothing: antialiased;
}

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--accents-2); border-radius: 3px; }
```

- [ ] **Step 2: Update layout.tsx with Geist font**

Replace `frontend/src/app/layout.tsx` with:
```tsx
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Vibe BG Music",
  description: "AI-powered background music player for Apple Music",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} font-[family-name:var(--font-geist-sans)]`}>
        {children}
      </body>
    </html>
  );
}
```

- [ ] **Step 3: Create API client**

Create `frontend/src/lib/api.ts`:
```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export const api = {
  health: () => request<{ connected: boolean }>("/api/health"),
  playlists: () => request<{ playlists: { name: string; track_count: number }[] }>("/api/playlists"),
  classify: (playlist: string) => request<{ status: string }>("/api/classify", { method: "POST", body: JSON.stringify({ playlist }) }),
  classifyStatus: () => request<{ status: string; progress: string }>("/api/classify/status"),
  categories: () => request<{ playlist_name: string | null; categories: Record<string, { database_id: number; name: string; artist: string; album: string; duration: number }[]> }>("/api/categories"),
  playCategory: (name: string) => request<{ playing: string }>(`/api/play/category/${encodeURIComponent(name)}`, { method: "POST" }),
  playCustom: (description: string) => request<{ playing: string; matched_count: number }>("/api/play/custom", { method: "POST", body: JSON.stringify({ description }) }),
  control: (action: string) => request("/api/player/control", { method: "POST", body: JSON.stringify({ action }) }),
  status: () => request<{ name: string; artist: string; database_id: number; position: number; duration: number; state: string; volume: number; category: string | null; queue_length: number; queue_index: number }>("/api/player/status"),
  setVolume: (volume: number) => request("/api/player/volume", { method: "POST", body: JSON.stringify({ volume }) }),
  seek: (position: number) => request("/api/player/seek", { method: "POST", body: JSON.stringify({ position }) }),
  queue: () => request<{ queue: { database_id: number; name: string; artist: string; duration: number }[]; current_index: number }>("/api/player/queue"),
  removeFromQueue: (index: number) => request(`/api/player/queue/${index}`, { method: "DELETE" }),
};
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/
git commit -m "feat: add frontend foundation (layout, globals, API client)"
```

---

## Task 7: Navbar Component

**Files:**
- Create: `frontend/src/components/Navbar.tsx`

- [ ] **Step 1: Implement Navbar.tsx**

```tsx
"use client";
import useSWR from "swr";
import { api } from "@/lib/api";

export default function Navbar() {
  const { data } = useSWR("health", api.health, { refreshInterval: 5000 });
  const connected = data?.connected ?? false;

  return (
    <nav className="sticky top-0 z-50 flex items-center justify-between h-16 px-6 border-b border-[var(--ds-gray-400)] backdrop-blur-md backdrop-saturate-[1.8] bg-black/80">
      <div className="flex items-center gap-3">
        <span className="text-lg font-bold tracking-[-0.02em] text-[var(--geist-foreground)]">
          Vibe BG Music
        </span>
        <span className="text-2xl font-extralight text-[var(--accents-2)]">/</span>
        <div className="flex gap-6 ml-4">
          <a href="#playlists" className="text-sm text-[var(--geist-foreground)] hover:text-[var(--geist-foreground)] transition-colors duration-150">Playlists</a>
          <a href="#categories" className="text-sm text-[var(--ds-gray-900)] hover:text-[var(--geist-foreground)] transition-colors duration-150">Categories</a>
        </div>
      </div>
      <div className="flex items-center gap-2 text-[13px] text-[var(--ds-gray-900)]">
        <span
          className={`w-2 h-2 rounded-full ${connected ? "bg-green-500 animate-pulse" : "bg-red-500"}`}
        />
        {connected ? "Apple Music Connected" : "Disconnected"}
      </div>
    </nav>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Navbar.tsx
git commit -m "feat: add Navbar component with connection status"
```

---

## Task 8: PlaylistGrid Component

**Files:**
- Create: `frontend/src/components/PlaylistGrid.tsx`

- [ ] **Step 1: Implement PlaylistGrid.tsx**

```tsx
"use client";
import { useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";

export default function PlaylistGrid({
  onClassified,
}: {
  onClassified: () => void;
}) {
  const { data, mutate } = useSWR("playlists", api.playlists);
  const [selected, setSelected] = useState<string | null>(null);
  const [classifyStatus, setClassifyStatus] = useState<string>("idle");
  const [progress, setProgress] = useState("");

  const playlists = data?.playlists ?? [];

  async function handleClassify() {
    if (!selected || classifyStatus === "classifying") return;
    setClassifyStatus("classifying");
    await api.classify(selected);

    const poll = setInterval(async () => {
      const s = await api.classifyStatus();
      setProgress(s.progress);
      if (s.status === "done") {
        clearInterval(poll);
        setClassifyStatus("done");
        onClassified();
      } else if (s.status === "error") {
        clearInterval(poll);
        setClassifyStatus("error");
      }
    }, 1000);
  }

  return (
    <section id="playlists">
      <h1 className="text-5xl font-extrabold tracking-[-0.04em] leading-tight mb-3">
        Select a Playlist
      </h1>
      <p className="text-base text-[var(--ds-gray-900)] mb-10 leading-relaxed">
        Choose a playlist from Apple Music, then classify tracks by genre with AI.
      </p>

      <div className="grid grid-cols-3 gap-px bg-[var(--ds-gray-400)] border border-[var(--ds-gray-400)] rounded-lg overflow-hidden mb-8">
        {playlists.map((p) => (
          <button
            key={p.name}
            onClick={() => setSelected(p.name)}
            className={`relative bg-[var(--ds-background-100)] p-6 text-left transition-colors duration-150 hover:bg-[var(--ds-gray-100)] ${
              selected === p.name ? "bg-[var(--ds-gray-100)]" : ""
            }`}
          >
            {selected === p.name && (
              <span className="absolute top-3 right-3 w-2 h-2 rounded-full bg-[var(--geist-foreground)]" />
            )}
            <div className="text-sm font-semibold text-[var(--geist-foreground)]">{p.name}</div>
            <div className="text-[13px] text-[var(--ds-gray-700)]">{p.track_count} tracks</div>
          </button>
        ))}
      </div>

      <div className="flex gap-3 mb-12">
        <button
          onClick={handleClassify}
          disabled={!selected || classifyStatus === "classifying"}
          className="h-10 px-4 bg-[var(--geist-foreground)] text-[var(--geist-background)] rounded-lg text-sm font-medium transition-colors duration-150 hover:bg-[#ccc] disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {classifyStatus === "classifying" ? `Classifying... ${progress}` : "Classify with AI"}
        </button>
        <button
          onClick={() => mutate()}
          className="h-10 px-4 bg-transparent text-[var(--geist-foreground)] border border-[var(--ds-gray-400)] rounded-lg text-sm font-medium transition-all duration-150 hover:bg-[var(--ds-gray-alpha-200)] hover:border-[var(--geist-foreground)]"
        >
          Refresh Playlists
        </button>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/PlaylistGrid.tsx
git commit -m "feat: add PlaylistGrid component with classify flow"
```

---

## Task 9: CategoryGrid Component

**Files:**
- Create: `frontend/src/components/CategoryGrid.tsx`

- [ ] **Step 1: Implement CategoryGrid.tsx**

```tsx
"use client";
import { useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";

export default function CategoryGrid() {
  const { data } = useSWR("categories", api.categories);
  const [customDesc, setCustomDesc] = useState("");
  const [customLoading, setCustomLoading] = useState(false);
  const [customError, setCustomError] = useState("");

  const categories = data?.categories ?? {};
  const playlistName = data?.playlist_name ?? "";
  const entries = Object.entries(categories);

  // +1 for custom pick card
  const totalCards = entries.length + 1;
  const fillerCount = (3 - (totalCards % 3)) % 3;

  async function handleCustomPlay() {
    if (!customDesc.trim() || customLoading) return;
    setCustomLoading(true);
    setCustomError("");
    try {
      await api.playCustom(customDesc);
    } catch (e: unknown) {
      setCustomError(e instanceof Error ? e.message : "No matching tracks");
    } finally {
      setCustomLoading(false);
    }
  }

  if (entries.length === 0) return null;

  return (
    <section>
      <div className="flex items-baseline gap-3 mb-6" id="categories">
        <h2 className="text-2xl font-bold tracking-[-0.02em]">Categories</h2>
        {playlistName && (
          <span className="text-sm text-[var(--ds-gray-700)]">from {playlistName}</span>
        )}
      </div>

      <div className="grid grid-cols-3 gap-px bg-[var(--ds-gray-400)] border border-[var(--ds-gray-400)] rounded-lg overflow-hidden">
        {/* Custom Pick Card */}
        <div className="bg-[var(--ds-background-100)] p-6 flex flex-col gap-3">
          <div className="text-sm font-semibold text-[var(--geist-foreground)]">Custom Pick</div>
          <input
            type="text"
            value={customDesc}
            onChange={(e) => setCustomDesc(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleCustomPlay()}
            placeholder="Describe what you want to hear..."
            className="w-full px-3 py-2 bg-[var(--ds-background-100)] border border-[var(--ds-gray-400)] rounded-md text-[13px] text-[var(--geist-foreground)] placeholder:text-[var(--accents-3)] outline-none transition-colors duration-150 focus:border-[var(--geist-foreground)] font-[family-name:var(--font-geist-sans)]"
          />
          <button
            onClick={handleCustomPlay}
            disabled={customLoading || !customDesc.trim()}
            className="self-start px-3.5 py-1.5 bg-[var(--geist-foreground)] text-[var(--geist-background)] rounded-md text-[13px] font-medium transition-colors duration-150 hover:bg-[#ccc] disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {customLoading ? "Selecting..." : "Play matching tracks"}
          </button>
          {customError && (
            <span className="text-xs text-red-400">{customError}</span>
          )}
        </div>

        {/* Category Cards */}
        {entries.map(([name, tracks]) => (
          <button
            key={name}
            onClick={() => api.playCategory(name)}
            className="group bg-[var(--ds-background-100)] p-6 flex flex-col gap-1 text-left transition-colors duration-150 hover:bg-[var(--ds-gray-100)]"
          >
            <div className="text-sm font-semibold text-[var(--geist-foreground)]">{name}</div>
            <div className="text-[13px] text-[var(--ds-gray-700)]">{tracks.length} tracks</div>
            <div className="text-xs text-[var(--accents-3)] mt-2 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
              Click to play &rarr;
            </div>
          </button>
        ))}

        {/* Filler Cards */}
        {Array.from({ length: fillerCount }).map((_, i) => (
          <div key={`filler-${i}`} className="bg-[var(--ds-background-100)]" />
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/CategoryGrid.tsx
git commit -m "feat: add CategoryGrid with custom pick and filler cards"
```

---

## Task 10: PlayerBar Component

**Files:**
- Create: `frontend/src/components/PlayerBar.tsx`

- [ ] **Step 1: Implement PlayerBar.tsx**

```tsx
"use client";
import { useCallback } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";

function formatTime(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

export default function PlayerBar({
  onToggleQueue,
}: {
  onToggleQueue: () => void;
}) {
  const { data } = useSWR("player-status", api.status, { refreshInterval: 1000 });

  const name = data?.name || "";
  const artist = data?.artist || "";
  const position = data?.position ?? 0;
  const duration = data?.duration ?? 0;
  const playerState = data?.state ?? "stopped";
  const isPlaying = playerState === "playing";
  const progress = duration > 0 ? (position / duration) * 100 : 0;

  const handleSeek = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!duration) return;
      const rect = e.currentTarget.getBoundingClientRect();
      const ratio = (e.clientX - rect.left) / rect.width;
      api.seek(ratio * duration);
    },
    [duration]
  );

  return (
    <div className="fixed bottom-0 left-0 right-0 h-20 bg-black/90 backdrop-blur-xl backdrop-saturate-[1.8] border-t border-[var(--ds-gray-400)] px-6 flex items-center gap-5 z-50">
      {/* Track Info */}
      <div className="flex items-center gap-3 w-[260px] min-w-0 shrink-0">
        <div className="w-12 h-12 rounded border border-[var(--ds-gray-400)] bg-[var(--ds-gray-200)] flex items-center justify-center text-lg text-[var(--ds-gray-700)] shrink-0">
          ♪
        </div>
        <div className="min-w-0">
          <div className="text-sm font-medium truncate">{name || "Not Playing"}</div>
          <div className="text-[13px] text-[var(--ds-gray-700)] truncate">{artist}</div>
        </div>
      </div>

      {/* Controls */}
      <div className="flex-1 flex flex-col items-center gap-1.5">
        <div className="flex items-center gap-6">
          <button onClick={() => api.control("prev")} className="w-8 h-8 flex items-center justify-center text-[var(--ds-gray-900)] hover:text-[var(--geist-foreground)] transition-colors duration-150">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M3 3h1.5v10H3V3zm9.5 5L6 13V3l6.5 5z"/></svg>
          </button>
          <button
            onClick={() => api.control(isPlaying ? "pause" : "resume")}
            className="w-9 h-9 rounded-full bg-[var(--geist-foreground)] text-[var(--geist-background)] flex items-center justify-center hover:bg-[#ccc] transition-colors duration-150"
          >
            {isPlaying ? (
              <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><rect x="3" y="2" width="4" height="12" rx="1"/><rect x="9" y="2" width="4" height="12" rx="1"/></svg>
            ) : (
              <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M4 2.5v11l9-5.5L4 2.5z"/></svg>
            )}
          </button>
          <button onClick={() => api.control("next")} className="w-8 h-8 flex items-center justify-center text-[var(--ds-gray-900)] hover:text-[var(--geist-foreground)] transition-colors duration-150">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M11.5 3H13v10h-1.5V3zM3.5 8L10 3v10L3.5 8z"/></svg>
          </button>
        </div>
        <div className="flex items-center gap-2 w-full max-w-[560px]">
          <span className="text-xs text-[var(--ds-gray-700)] font-[family-name:var(--font-geist-mono)] tabular-nums min-w-9 text-center">
            {formatTime(position)}
          </span>
          <div
            className="flex-1 h-1 bg-[var(--ds-gray-alpha-400)] rounded-sm cursor-pointer group relative"
            onClick={handleSeek}
          >
            <div className="h-full bg-[var(--geist-foreground)] rounded-sm relative" style={{ width: `${progress}%` }}>
              <span className="absolute -right-[5px] -top-[3px] w-2.5 h-2.5 rounded-full bg-[var(--geist-foreground)] opacity-0 group-hover:opacity-100 transition-opacity duration-150" />
            </div>
          </div>
          <span className="text-xs text-[var(--ds-gray-700)] font-[family-name:var(--font-geist-mono)] tabular-nums min-w-9 text-center">
            {formatTime(duration)}
          </span>
        </div>
      </div>

      {/* Volume + Queue */}
      <div className="flex items-center gap-3 w-[200px] justify-end shrink-0">
        <VolumeControl volume={data?.volume ?? 50} />
        <button
          onClick={onToggleQueue}
          className="px-3 py-1.5 border border-[var(--ds-gray-400)] rounded-md text-[13px] text-[var(--ds-gray-900)] hover:text-[var(--geist-foreground)] hover:border-[var(--geist-foreground)] transition-all duration-150"
        >
          Queue
        </button>
      </div>
    </div>
  );
}

function VolumeControl({ volume }: { volume: number }) {
  const handleVolumeChange = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const ratio = (e.clientX - rect.left) / rect.width;
    api.setVolume(Math.round(ratio * 100));
  }, []);

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-[var(--ds-gray-900)]">♪</span>
      <div className="w-20 h-1 bg-[var(--ds-gray-alpha-400)] rounded-sm cursor-pointer" onClick={handleVolumeChange}>
        <div className="h-full bg-[var(--geist-foreground)] rounded-sm" style={{ width: `${volume}%` }} />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/PlayerBar.tsx
git commit -m "feat: add PlayerBar with playback controls, progress, volume"
```

---

## Task 11: QueuePanel Component

**Files:**
- Create: `frontend/src/components/QueuePanel.tsx`

- [ ] **Step 1: Implement QueuePanel.tsx**

```tsx
"use client";
import useSWR from "swr";
import { api } from "@/lib/api";

export default function QueuePanel({
  visible,
  onClose,
}: {
  visible: boolean;
  onClose: () => void;
}) {
  const { data, mutate } = useSWR(visible ? "queue" : null, api.queue, { refreshInterval: 2000 });

  const queue = data?.queue ?? [];
  const currentIndex = data?.current_index ?? 0;

  async function handleRemove(index: number) {
    await api.removeFromQueue(index);
    mutate();
  }

  if (!visible) return null;

  return (
    <div className="fixed right-4 bottom-[88px] w-[360px] max-h-[400px] bg-[var(--ds-background-200)] border border-[var(--ds-gray-400)] rounded-lg p-4 overflow-y-auto z-40">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[13px] font-semibold text-[var(--ds-gray-900)] uppercase tracking-wider">
          Up Next
        </span>
        <button
          onClick={onClose}
          className="p-1 text-[var(--ds-gray-900)] hover:text-[var(--geist-foreground)] transition-colors duration-150 rounded"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M4 6L8 10L12 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      </div>

      {queue.map((track, i) => (
        <div
          key={`${track.database_id}-${i}`}
          className="flex items-center justify-between px-2 py-2 rounded-md transition-colors duration-150 hover:bg-[var(--ds-gray-alpha-200)]"
        >
          <div className="min-w-0 flex flex-col gap-0.5">
            <span className={`text-[13px] truncate ${i === currentIndex ? "text-[var(--geist-foreground)] font-medium" : "text-[var(--ds-gray-900)]"}`}>
              {track.name}
            </span>
            <span className="text-xs text-[var(--ds-gray-700)]">{track.artist}</span>
          </div>
          {i === currentIndex ? (
            <span className="text-[11px] font-medium text-[var(--geist-foreground)] shrink-0">Playing</span>
          ) : (
            <button
              onClick={() => handleRemove(i)}
              className="w-6 h-6 flex items-center justify-center text-[var(--accents-3)] hover:text-[var(--geist-foreground)] hover:bg-[var(--ds-gray-alpha-200)] rounded transition-colors duration-150 shrink-0"
            >
              ×
            </button>
          )}
        </div>
      ))}

      {queue.length === 0 && (
        <div className="text-[13px] text-[var(--ds-gray-700)] text-center py-8">
          No tracks in queue
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/QueuePanel.tsx
git commit -m "feat: add QueuePanel with minimize button and track removal"
```

---

## Task 12: Main Page (Compose All Components)

**Files:**
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: Implement page.tsx**

Replace `frontend/src/app/page.tsx` with:
```tsx
"use client";
import { useState } from "react";
import Navbar from "@/components/Navbar";
import PlaylistGrid from "@/components/PlaylistGrid";
import CategoryGrid from "@/components/CategoryGrid";
import PlayerBar from "@/components/PlayerBar";
import QueuePanel from "@/components/QueuePanel";
import { mutate } from "swr";

export default function Home() {
  const [showCategories, setShowCategories] = useState(false);
  const [queueVisible, setQueueVisible] = useState(false);

  function handleClassified() {
    setShowCategories(true);
    mutate("categories");
  }

  return (
    <>
      <Navbar />
      <main className="max-w-[1100px] mx-auto px-6 py-12 pb-24">
        <PlaylistGrid onClassified={handleClassified} />
        {showCategories && (
          <>
            <hr className="border-t border-[var(--ds-gray-400)] my-0 mb-12" />
            <CategoryGrid />
          </>
        )}
      </main>
      <PlayerBar onToggleQueue={() => setQueueVisible((v) => !v)} />
      <QueuePanel visible={queueVisible} onClose={() => setQueueVisible(false)} />
    </>
  );
}
```

- [ ] **Step 2: Verify frontend builds**

```bash
cd /Users/mitsuha/vibe-bg-music/frontend
bun run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/page.tsx
git commit -m "feat: compose main page with all components"
```

---

## Task 13: Integration Test & Final Cleanup

- [ ] **Step 1: Start backend**

```bash
cd /Users/mitsuha/vibe-bg-music/backend
uv run uvicorn main:app --host 0.0.0.0 --port 8000 &
```

- [ ] **Step 2: Start frontend**

```bash
cd /Users/mitsuha/vibe-bg-music/frontend
bun dev &
```

- [ ] **Step 3: Manual integration test**

Open `http://localhost:3000`. Verify:
1. Navbar shows connection status
2. Playlists load from Apple Music
3. Select playlist → Classify → categories appear
4. Click category → Apple Music starts playing
5. PlayerBar shows track info, progress updates
6. Play/pause/next/prev controls work
7. Volume control works
8. Progress bar seek works
9. Queue panel opens/closes, shows tracks, remove works
10. Custom pick card: type description → matching tracks play
11. Filler cards fill incomplete rows
12. Auto-continuation when track ends

- [ ] **Step 4: Fix any issues found**

- [ ] **Step 5: Clean up mockup file**

```bash
rm /Users/mitsuha/vibe-bg-music/mockup.html
```

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "feat: complete Vibe BG Music v1.0"
```
