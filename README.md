# Vibe BG Music

AI-powered background music player for Apple Music. Classifies your playlist tracks by genre using GPT, then plays random tracks from your chosen category with auto-continuation.

## Features

- Control Apple Music via osascript
- GPT-powered track classification (customizable language, category count, and direction)
- Custom description matching — describe what you want to hear
- Web UI styled after [nextjs.org](https://nextjs.org) design language
- Playback controls: play/pause, next/prev, seek, volume
- Queue management with jump-to-track and removal
- Album artwork display
- LAN accessible — control from any device on your network

## Architecture

```
Frontend (Next.js + Bun)  ◄── REST API ──►  Backend (FastAPI + uv)  ──► Apple Music (osascript)
       :3000                                      :8000                        ↕
                                                    └──► OpenAI API (GPT)
```

## Requirements

- macOS with Apple Music
- [uv](https://docs.astral.sh/uv/) — Python package manager
- [Bun](https://bun.sh/) — JavaScript runtime
- OpenAI-compatible API key

## Quick Start

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env with your API credentials
```

### 2. Start backend

```bash
cd backend
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

### 3. Start frontend

```bash
cd frontend
bun install
bun dev
```

Open [http://localhost:3000](http://localhost:3000).

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | API key for OpenAI-compatible service | (required) |
| `OPENAI_BASE_URL` | API base URL | `https://api.openai.com/v1` |
| `GPT_LANGUAGE` | Language for category names (`en`, `zh-CN`, `ja`, etc.) | `en` |
| `GPT_CATEGORY_COUNT` | Target number of categories (leave empty for auto) | (empty) |
| `GPT_CATEGORY_DIRECTION` | Classification direction/description | (empty) |

## Docker (Frontend)

The frontend can be deployed as a Docker container. Set `NEXT_PUBLIC_API_URL` at build time to point to your backend.

```bash
cd frontend
docker build --build-arg NEXT_PUBLIC_API_URL=http://your-mac-ip:8000 -t vibe-bg-music-web .
docker run -p 3000:3000 vibe-bg-music-web
```

> **Note:** The backend must run on macOS (requires osascript + Apple Music). Only the frontend can be containerized.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Apple Music connection status |
| GET | `/api/playlists` | List all playlists |
| POST | `/api/classify` | Classify playlist tracks |
| GET | `/api/classify/status` | Classification progress |
| GET | `/api/categories` | Get classification results |
| POST | `/api/play/category/{name}` | Play a category |
| POST | `/api/play/custom` | Play by description |
| POST | `/api/player/control` | Playback control (pause/resume/next/prev) |
| GET | `/api/player/status` | Current playback state |
| GET | `/api/player/artwork` | Current track album art |
| POST | `/api/player/volume` | Set volume |
| POST | `/api/player/seek` | Seek to position |
| POST | `/api/player/jump/{index}` | Jump to queue position |
| GET | `/api/player/queue` | Get queue |
| DELETE | `/api/player/queue/{index}` | Remove from queue |

## License

MIT
