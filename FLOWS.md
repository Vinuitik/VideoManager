# VideoManager — FLOWS Index

Personal yt-dlp frontend. One URL in → video downloaded → optional FFmpeg post-processing.

## Subsystem FLOWS

| File | Covers |
|------|--------|
| [backend/FLOWS.md](backend/FLOWS.md) | FastAPI routes, yt-dlp download (poll + WS), FFmpeg, in-memory job store |
| [frontend/FLOWS.md](frontend/FLOWS.md) | React pages, routing, Tailwind patterns, dev vs prod proxy |

---

## Overall Request Lifecycle

```
Browser → nginx :80
  ├── GET /           → serves React SPA (pre-compiled, static files in nginx image)
  ├── GET /poll       → same SPA, React Router handles it client-side
  ├── GET /websocket  → same SPA
  │
  ├── /api/*          → proxied to FastAPI backend :8000 (HTTP)
  └── /api/v2/download → proxied with WS upgrade headers (WebSocket)
```

## Container Map

| Container | Image built from | Exposes |
|-----------|-----------------|---------|
| `backend` | `backend/Dockerfile` (python:3.12-slim + ffmpeg + yt-dlp) | port 8000 (internal only) |
| `nginx`   | `nginx/Dockerfile` (multi-stage: Node builds React → nginx:alpine serves it) | port 80 (public) |

Volume: `C:\Users\ACER\Desktop\YT-Videos` → `/videos` inside backend container

---

## Common Tasks — Where to Go

### I want to add a new feature / page
→ [frontend/FLOWS.md](frontend/FLOWS.md) — "To add a new page" section

### I want to change how videos are downloaded (quality, format, subtitles)
→ [backend/FLOWS.md](backend/FLOWS.md) — `services/downloader.build_ydl_opts()`

### I want to add a new FFmpeg effect (e.g. denoise, speed up)
→ [backend/FLOWS.md](backend/FLOWS.md) — `services/processor.PRESETS`

### I want to debug a failed download
→ [backend/FLOWS.md](backend/FLOWS.md) — "Debugging" section

### I want to understand how polling differs from WebSocket
→ [backend/FLOWS.md](backend/FLOWS.md) — Download Flow A vs B
→ [frontend/FLOWS.md](frontend/FLOWS.md) — DownloadPoll vs DownloadWS page flows

### I want to scale this for multiple users
→ [backend/FLOWS.md](backend/FLOWS.md) — "Scaling" section

### I want to change the port nginx listens on
→ `docker-compose.yml` → `nginx.ports`

### I want to change the videos folder
→ `docker-compose.yml` → `backend.volumes` + `backend.environment.VIDEOS_DIR`
