# Vibe BG Music — Design Spec

## Overview

A local application that controls Apple Music via osascript, uses GPT to classify playlist tracks by genre, and provides a WebUI for browsing categories and playing music with auto-continuation.

## Architecture

```
┌─────────────────────┐     REST API     ┌─────────────────────┐
│   Next.js Frontend  │ ◄──────────────► │   FastAPI Backend   │
│   (Bun + TS)        │                  │   (uv + Python)     │
│   Port: 3000        │                  │   Port: 8000        │
└─────────────────────┘                  └────────┬────────────┘
                                                  │ osascript
                                                  ▼
                                         ┌─────────────────────┐
                                         │    Apple Music       │
                                         └─────────────────────┘
                                                  ▲
                                                  │ OpenAI API
                                         ┌─────────────────────┐
                                         │    GPT (classify)    │
                                         └─────────────────────┘
```

Note: The OpenAI API arrow originates from the FastAPI backend, not from Apple Music. The backend calls both osascript and OpenAI.

Frontend polls backend every 1 second for player status. No WebSocket/SSE — Apple Music has no event callbacks so backend polls osascript anyway, making real-time push unnecessary. Worst-case UI lag is ~2 seconds (backend poll + frontend poll), acceptable for a background music player.

## Project Structure

```
vibe-bg-music/
├── backend/
│   ├── pyproject.toml
│   ├── main.py           # FastAPI app, CORS, routes
│   ├── apple_music.py    # osascript wrapper
│   ├── classifier.py     # OpenAI classification logic
│   └── player.py         # Queue management, auto-continuation
├── frontend/
│   ├── package.json
│   ├── tailwind.config.ts
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   └── globals.css
│   │   ├── components/
│   │   │   ├── Navbar.tsx
│   │   │   ├── PlaylistGrid.tsx
│   │   │   ├── CategoryGrid.tsx
│   │   │   ├── PlayerBar.tsx
│   │   │   └── QueuePanel.tsx
│   │   └── lib/
│   │       └── api.ts     # Backend API client
│   └── ...
├── .env                   # OPENAI_API_KEY, OPENAI_BASE_URL (loaded by backend via python-dotenv from project root)
└── mockup.html
```

## Backend

### Apple Music Control (`apple_music.py`)

All interactions via `subprocess.run(["osascript", "-e", script])`. All playlist/track names must be escaped (replace `"` with `\"` and `\` with `\\`) before embedding in AppleScript strings.

Functions:

- `is_running()` — check if Apple Music is currently running (returns bool)
- `get_playlists()` — list all user playlist names + track counts
- `get_tracks(playlist_name)` — get all tracks with fields: name, artist, album, duration, database_id (Apple Music's unique integer ID per track)
- `play_track(playlist_name, database_id)` — play a specific track by its database ID (not by name, since names are not unique)
- `pause()` / `resume()` / `next_track()` / `prev_track()`
- `get_player_state()` — returns: track name, artist, database_id, position, duration, player state (playing/paused/stopped)
- `set_position(seconds)` — seek to a specific position in the current track
- `get_volume()` / `set_volume(level)`

If Apple Music is not running, all functions raise an `AppleMusicNotRunningError`. The API layer catches this and returns HTTP 503 with a message instructing the user to open Apple Music.

### Classification (`classifier.py`)

Uses OpenAI SDK with custom `base_url` and `api_key` from env vars.

Sends batch of track info (name + artist + album) to GPT via `client.responses.create()`. Prompt instructs GPT to decide appropriate genre granularity and output all category names in the language specified by `GPT_LANGUAGE` env var. Returns structured JSON:

```json
{
  "categories": {
    "Indie Rock": [
      {"name": "Song A", "artist": "Artist X", "database_id": 12345},
      ...
    ],
    "Synthwave": [...],
    ...
  }
}
```

For large playlists (100+ tracks), splits into batches of 50. The first batch establishes category names; subsequent batches receive those names as guidance to ensure consistent naming. Results are merged by category name. If GPT introduces a new category in a later batch, it is kept.

GPT response is validated: parse JSON, verify all returned tracks exist in the original playlist (by database_id). Tracks GPT omits are placed in an "Uncategorized" fallback category. Malformed JSON triggers a retry (up to 2 retries per batch).

#### Custom Description Matching

`pick_by_description(description: str, tracks: list[Track]) -> list[Track]`

Sends all classified tracks (from current playlist) along with a user-provided natural language description to GPT. GPT selects tracks that match the description and returns their database_ids. Example descriptions: "适合下雨天听的歌", "upbeat workout music", "带有钢琴的安静曲子".

Uses `client.responses.create()` with structured JSON output: `{"track_ids": [12345, 67890, ...]}`. Validated against known tracks. Returns empty list if none match (frontend shows "No matching tracks").

### Player Management (`player.py`)

`PlayerState` class maintains:
- `current_category: str | None`
- `queue: list[Track]` — shuffled tracks from selected category
- `current_index: int`
- `is_monitoring: bool`
- `categories: dict[str, list[Track]]` — classification results (owned by PlayerState, populated by classifier)

Background task (asyncio) polls Apple Music every 1 second. Track-end detection: when `position >= duration - 2` AND state becomes `paused` or `stopped` on the next poll, trigger auto-advance. This handles Apple Music's behavior of stopping at the end of a track.

"prev" action: if `current_index > 0`, decrement and play the previous track in the queue. If at index 0, restart the current track from the beginning.

Removing the currently playing track from the queue: skip to the next track. If it was the last track, reshuffle and restart.

When queue exhausts, reshuffles same category and continues.

Note: single `PlayerState` instance — multiple LAN clients share the same playback state (one Apple Music, one queue). This is by design.

### REST API (`main.py`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Check Apple Music connection status |
| GET | `/api/playlists` | List all playlists |
| POST | `/api/classify` | Classify a playlist's tracks (body: `{playlist: "name"}`). Async: returns `{status: "classifying"}` immediately, client polls `/api/classify/status` |
| GET | `/api/classify/status` | Classification progress: `{status: "idle"|"classifying"|"done"|"error", progress?: "2/4 batches"}` |
| GET | `/api/categories` | Get current classification results |
| POST | `/api/play/category/{name}` | Start playing a category (returns 400 if category is empty) |
| POST | `/api/play/custom` | Play by description (body: `{description: "text"}`). Calls GPT to pick matching tracks, builds queue, starts playback. Returns 400 if no tracks match |
| POST | `/api/player/control` | Control playback (body: `{action: "pause"|"resume"|"next"|"prev"}`) |
| GET | `/api/player/status` | Current playback state (polled every 1s) |
| POST | `/api/player/volume` | Set volume (body: `{volume: 0-100}`) |
| POST | `/api/player/seek` | Seek to position (body: `{position: seconds}`) |
| GET | `/api/player/queue` | Get current queue |
| DELETE | `/api/player/queue/{index}` | Remove track from queue |

CORS enabled for all origins (LAN use).

## Frontend

### Design Language (from nextjs.org)

- Pure black background (`#000`), white foreground (`#ededed`), gray accents
- Geist font family (fallback Inter), Geist Mono for numbers
- 1px border grid cards with `gap: 1px` separator effect
- Buttons: primary (white bg, black text), secondary (transparent, border)
- `backdrop-filter: saturate(180%) blur()` on nav and player bar
- `letter-spacing: -0.04em` on hero titles
- `150ms` transition duration throughout
- Monochromatic — no colorful gradients on UI elements

### Components

**Navbar** — sticky top, logo "Vibe BG Music", nav links (Playlists/Categories), connection status indicator with green pulse dot. Status backed by `GET /api/health`. Red dot + "Disconnected" if Apple Music is not running.

**PlaylistGrid** — 3-column grid of playlist cards. Click to select (shows dot indicator). "Classify with AI" primary button + "Refresh Playlists" secondary button below.

**ClassifyingState** — while classification is in progress (polling `/api/classify/status`), show a loading indicator with batch progress (e.g., "Classifying... 2/4 batches"). Disable "Classify" button during this time.

**CategoryGrid** — 3-column grid of category cards after classification. Shows category name + track count. Hover reveals "Click to play →". Click starts random playback of that category. The first card in the grid is a special **CustomPickCard**: an input field with placeholder "Describe what you want to hear..." and a submit button. User types a description, submits, backend calls GPT to pick matching tracks from the full playlist and starts playback. While GPT is selecting, show a loading spinner on the card. If the total card count (CustomPickCard + category cards) is not a multiple of 3, append empty placeholder cards (same background, no content, no hover effect) to fill the last row.

**PlayerBar** — fixed bottom bar (80px). Left: artwork placeholder + track name + artist. Center: prev/play-pause/next buttons + clickable progress bar (seek on click) with monospace timestamps. Right: volume slider + "Queue" button.

**QueuePanel** — floating panel above player bar (right side). Shows "Up Next" list. Current track highlighted. Each queued track has remove button.

### Data Fetching

Uses `swr` with `refreshInterval: 1000` for `/api/player/status` polling. Other endpoints fetched on demand.

## Environment Configuration

```env
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
GPT_LANGUAGE=zh-CN
```

`GPT_LANGUAGE` controls the language GPT uses for category names and any text output (e.g., `zh-CN` → "独立摇滚", `en` → "Indie Rock", `ja` → "インディーロック"). Defaults to `en` if not set.

Supports any OpenAI-compatible API service.

## Tech Stack

**Backend:** Python 3.12+, FastAPI, uvicorn, openai SDK, python-dotenv (managed by uv)

**Frontend:** Next.js 15, TypeScript, Tailwind CSS, swr (managed by Bun)

**No database. No external infrastructure. LAN accessible.**
