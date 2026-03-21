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

Frontend polls backend every 1 second for player status. No WebSocket/SSE — Apple Music has no event callbacks so backend polls osascript anyway, making real-time push unnecessary.

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
├── .env                   # OPENAI_API_KEY, OPENAI_BASE_URL
└── mockup.html
```

## Backend

### Apple Music Control (`apple_music.py`)

All interactions via `subprocess.run(["osascript", "-e", script])`. Functions:

- `get_playlists()` — list all user playlist names + track counts
- `get_tracks(playlist_name)` — get all tracks (name, artist, album, duration) from a playlist
- `play_track(playlist_name, track_name)` — play a specific track
- `pause()` / `resume()` / `next_track()`
- `get_player_state()` — returns: track name, artist, position, duration, player state (playing/paused/stopped)
- `get_volume()` / `set_volume(level)`

### Classification (`classifier.py`)

Uses OpenAI SDK with custom `base_url` and `api_key` from env vars.

Sends batch of track info (name + artist + album) to GPT via Response API. Prompt instructs GPT to decide appropriate genre granularity and return structured JSON:

```json
{
  "categories": {
    "Indie Rock": [
      {"name": "Song A", "artist": "Artist X"},
      ...
    ],
    "Synthwave": [...],
    ...
  }
}
```

For large playlists (100+ tracks), splits into batches and merges results.

### Player Management (`player.py`)

`PlayerState` class maintains:
- `current_category: str | None`
- `queue: list[Track]` — shuffled tracks from selected category
- `current_index: int`
- `is_monitoring: bool`

Background task (asyncio) polls Apple Music every 1 second. When current track ends (position near 0 + state is paused/stopped), plays next in queue. When queue exhausts, reshuffles same category and continues.

### REST API (`main.py`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/playlists` | List all playlists |
| POST | `/api/classify` | Classify a playlist's tracks (body: `{playlist: "name"}`) |
| GET | `/api/categories` | Get current classification results |
| POST | `/api/play/category/{name}` | Start playing a category |
| POST | `/api/player/control` | Control playback (body: `{action: "pause"|"resume"|"next"|"prev"}`) |
| GET | `/api/player/status` | Current playback state (polled every 1s) |
| POST | `/api/player/volume` | Set volume (body: `{volume: 0-100}`) |
| GET | `/api/player/queue` | Get current queue |
| DELETE | `/api/player/queue/{index}` | Remove track from queue |

CORS enabled for `localhost:3000`.

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

**Navbar** — sticky top, logo "Vibe BG Music", nav links (Playlists/Categories), connection status indicator with green pulse dot.

**PlaylistGrid** — 3-column grid of playlist cards. Click to select (shows dot indicator). "Classify with AI" primary button + "Refresh Playlists" secondary button below.

**CategoryGrid** — 3-column grid of category cards after classification. Shows category name + track count. Hover reveals "Click to play →". Click starts random playback of that category.

**PlayerBar** — fixed bottom bar (80px). Left: artwork placeholder + track name + artist. Center: prev/play-pause/next buttons + progress bar with monospace timestamps. Right: volume slider + "Queue" button.

**QueuePanel** — floating panel above player bar (right side). Shows "Up Next" list. Current track highlighted. Each queued track has remove button.

### Data Fetching

Uses `swr` with `refreshInterval: 1000` for `/api/player/status` polling. Other endpoints fetched on demand.

## Environment Configuration

```env
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
```

Supports any OpenAI-compatible API service.

## Tech Stack

**Backend:** Python 3.12+, FastAPI, uvicorn, openai SDK, python-dotenv (managed by uv)

**Frontend:** Next.js 15, TypeScript, Tailwind CSS, swr (managed by Bun)

**No database. No external infrastructure. LAN accessible.**
