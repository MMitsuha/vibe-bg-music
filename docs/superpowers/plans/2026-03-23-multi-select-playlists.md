# Multi-Select Playlists Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to select multiple playlists, merge their tracks, and classify them together as one combined set.

**Architecture:** Add `playlist_name` field to `Track` so each track knows its source playlist. Backend accepts a list of playlist names, fetches and merges tracks from all, then classifies the combined set. Frontend switches from single-select to toggle multi-select.

**Tech Stack:** Python/FastAPI backend, Next.js/React frontend, AppleScript for Apple Music control.

---

### Task 1: Add `playlist_name` to Track dataclass

**Files:**
- Modify: `backend/player.py:6-11`

- [ ] **Step 1: Add field to Track**

```python
@dataclass
class Track:
    database_id: int
    name: str
    artist: str
    album: str
    duration: float
    playlist_name: str = ""
```

- [ ] **Step 2: Update `set_categories` to preserve playlist_name**

In `PlayerState.set_categories` (line 26-38), add `playlist_name` to Track construction:

```python
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
                playlist_name=t.get("playlist_name", ""),
            )
            for t in tracks
        ]
```

- [ ] **Step 3: Change `playlist_name` to `playlist_names` on PlayerState**

Change line 16 from:
```python
playlist_name: str | None = None
```
to:
```python
playlist_names: list[str] = field(default_factory=list)
```

- [ ] **Step 4: Commit**

```bash
git add backend/player.py
git commit -m "feat: add playlist_name to Track, support multiple playlist names in state"
```

---

### Task 2: Update backend API to accept multiple playlists

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Change ClassifyRequest model**

```python
class ClassifyRequest(BaseModel):
    playlists: list[str]
```

- [ ] **Step 2: Update `/api/classify` to merge tracks from all playlists**

Replace the `classify` endpoint:

```python
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
                tracks = apple_music.get_tracks(pl)
                for t in tracks:
                    t["playlist_name"] = pl
                all_tracks.extend(tracks)
            state._all_tracks = all_tracks
            def on_progress(p: str):
                state.classify_progress = p
            loop = asyncio.get_event_loop()
            categories = await loop.run_in_executor(
                None, lambda: classifier.classify_tracks(all_tracks, on_progress)
            )
            state.set_categories(categories)
            state.classify_status = "done"
        except Exception as e:
            state.classify_status = "error"
            state.classify_progress = str(e)

    asyncio.create_task(run_classification())
    return {"status": "classifying"}
```

- [ ] **Step 3: Update all `play_track` calls to use track's playlist_name**

There are 4 places that call `apple_music.play_track(state.playlist_name, ...)`. Each must use the track's own `playlist_name`:

1. `monitor_playback` (~line 28):
```python
apple_music.play_track(track.playlist_name, track.database_id)
```
Also update the guard from `if track and state.playlist_name:` to `if track and track.playlist_name:`.

2. `play_category` (~line 149):
```python
apple_music.play_track(track.playlist_name, track.database_id)
```

3. `play_custom` (~line 175):
```python
apple_music.play_track(track.playlist_name, track.database_id)
```

4. `player_control` next/prev (~line 194, 198):
```python
# next
if track and track.playlist_name:
    apple_music.play_track(track.playlist_name, track.database_id)
# prev
if track and track.playlist_name:
    apple_music.play_track(track.playlist_name, track.database_id)
```

5. `player_jump` (~line 249):
```python
apple_music.play_track(track.playlist_name, track.database_id)
```

6. `remove_from_queue` (~line 273):
```python
apple_music.play_track(next_track.playlist_name, next_track.database_id)
```

- [ ] **Step 4: Update `/api/categories` response**

Change `state.playlist_name` to `state.playlist_names`:
```python
@app.get("/api/categories")
def get_categories():
    return {
        "playlist_names": state.playlist_names,
        "categories": {
            name: [{"database_id": t.database_id, "name": t.name, "artist": t.artist, "album": t.album, "duration": t.duration} for t in tracks]
            for name, tracks in state.categories.items()
        }
    }
```

- [ ] **Step 5: Update `play_custom` Track construction to include playlist_name**

In `play_custom`, where matched tracks are converted to Track objects:
```python
matched_as_tracks = [
    Track(
        database_id=t["database_id"],
        name=t["name"],
        artist=t["artist"],
        album=t.get("album", ""),
        duration=t.get("duration", 0),
        playlist_name=t.get("playlist_name", ""),
    )
    for t in matched
]
```

- [ ] **Step 6: Commit**

```bash
git add backend/main.py
git commit -m "feat: accept multiple playlists in classify, use per-track playlist_name for playback"
```

---

### Task 3: Update frontend API and PlaylistGrid for multi-select

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/components/PlaylistGrid.tsx`

- [ ] **Step 1: Update api.ts classify call**

Change from:
```typescript
classify: (playlist: string) => request<{ status: string }>("/api/classify", { method: "POST", body: JSON.stringify({ playlist }) }),
```
to:
```typescript
classify: (playlists: string[]) => request<{ status: string }>("/api/classify", { method: "POST", body: JSON.stringify({ playlists }) }),
```

- [ ] **Step 2: Update PlaylistGrid to multi-select**

Change state from single string to Set:
```typescript
const [selected, setSelected] = useState<Set<string>>(new Set());
```

Toggle handler:
```typescript
function togglePlaylist(name: string) {
    setSelected((prev) => {
        const next = new Set(prev);
        if (next.has(name)) next.delete(name);
        else next.add(name);
        return next;
    });
}
```

Update button onClick from `() => setSelected(p.name)` to `() => togglePlaylist(p.name)`.

Update selected indicator from `selected === p.name` to `selected.has(p.name)`.

Update classify call from `api.classify(selected)` to `api.classify([...selected])`.

Update disabled check from `!selected` to `selected.size === 0`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/components/PlaylistGrid.tsx
git commit -m "feat: multi-select playlists in frontend"
```

---

### Task 4: Manual verification

- [ ] **Step 1: Start backend and frontend**

```bash
cd backend && source .venv/bin/activate && uvicorn main:app --reload &
cd frontend && npm run dev &
```

- [ ] **Step 2: Verify multi-select works**

1. Open the app in browser
2. Click multiple playlists — each should toggle selected state with the dot indicator
3. Click "Classify with AI" — should classify tracks from all selected playlists
4. Play a category — tracks from different playlists should all play correctly
