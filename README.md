# VideoManager

Personal yt-dlp frontend with FFmpeg post-processing. Paste URL → download → boost volume.

## Quick Start

```bash
docker compose up --build
# open http://localhost
```

> **Dev mode** (hot reload):
> ```bash
> docker compose up backend          # terminal 1
> cd frontend && npm install && npm run dev  # terminal 2 — http://localhost:5173
> ```

## Architecture

```
Browser
  └── nginx :80
        ├── /          → React SPA (compiled static files)
        └── /api/*     → FastAPI :8000
                            ├── yt-dlp  (download)
                            └── ffmpeg  (post-process)
                            └── /videos (→ C:\Users\ACER\Desktop\YT-Videos)
```

## FLOWS (subsystem detail)

- [backend/FLOWS.md](backend/FLOWS.md) — download flows (polling + WebSocket), CRUD, FFmpeg
- [frontend/FLOWS.md](frontend/FLOWS.md) — React page flows, Tailwind cheatsheet, dev vs prod routing

## Pages

| Route        | Purpose                                          |
|--------------|--------------------------------------------------|
| `/`          | Library — list and delete downloaded videos      |
| `/poll`      | Download via polling (Version A — Redis pattern) |
| `/websocket` | Download via WebSocket (Version B — real-time)   |
