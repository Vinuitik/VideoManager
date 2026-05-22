# VideoManager — FLOWS Index

Personal yt-dlp frontend. Paste URL → download with progress → stream from library.

## Subsystem FLOWS

| File | Covers |
|------|--------|
| [backend/FLOWS.md](backend/FLOWS.md) | FastAPI routes, yt-dlp download (poll + WS), FFmpeg, in-memory job store, Prometheus metrics |
| [frontend/FLOWS.md](frontend/FLOWS.md) | React pages, routing, Tailwind patterns, WS multiplexing, video player |
| [k6/README.md](k6/README.md) | Load test scenarios, how to run, how to read results |

---

## Overall Request Lifecycle

```
Browser → nginx :80
  ├── GET /           → serves React SPA (pre-compiled static files in nginx image)
  ├── GET /poll       → same SPA, React Router handles it client-side
  ├── GET /websocket  → same SPA
  │
  ├── GET /videos/*   → nginx serves video files DIRECTLY from disk (range requests, seeking works)
  │                     backend is NOT involved in video playback
  │
  ├── /api/*          → proxied to FastAPI backend :8000 (HTTP)
  └── /api/v2/download → proxied with WS upgrade headers (WebSocket)
```

## Container Map

| Container    | Built from | Exposes | Purpose |
|--------------|-----------|---------|---------|
| `backend`    | `backend/Dockerfile` | 8000 (internal) | FastAPI, yt-dlp, ffmpeg |
| `nginx`      | `nginx/Dockerfile` (multi-stage) | 80 (public) | SPA + /videos streaming + API proxy |
| `prometheus` | `prom/prometheus` (official image) | 9090 | Scrapes `/metrics` from backend |
| `grafana`    | `grafana/grafana` (official image)  | 3000 | Dashboards — open http://localhost:3000, no login |

Volume: `C:\Users\ACER\Desktop\YT-Videos` → `/videos` in both `backend` and `nginx`

---

## Common Tasks — Where to Go

### I want to add a new page or feature
→ [frontend/FLOWS.md](frontend/FLOWS.md) — "To add a new page" section

### I want to change video quality / format / subtitles
→ [backend/FLOWS.md](backend/FLOWS.md) — `services/downloader.build_ydl_opts()`

### I want to add a new FFmpeg effect
→ [backend/FLOWS.md](backend/FLOWS.md) — `services/processor.PRESETS`

### I want to debug a failed download
→ [backend/FLOWS.md](backend/FLOWS.md) — "Debugging Guide" table

### I want to see live latency / error rates / throughput
→ Open http://localhost:3000 → VideoManager dashboard

### I want to run a load test
→ [k6/README.md](k6/README.md) — install + run commands

### I want to understand polling vs WebSocket differences
→ Run both pages side-by-side. Poll bar jumps every ~1s. WS bar moves per chunk (sub-second).
→ [backend/FLOWS.md](backend/FLOWS.md) — Download Flow A vs B
→ [frontend/FLOWS.md](frontend/FLOWS.md) — DownloadPoll vs DownloadWS page flows

### I want to add more Prometheus metrics (e.g. active downloads count)
→ `backend/main.py` — import `prometheus_client`, add `Gauge` or `Counter` before `Instrumentator()`

### I want to add a Grafana panel
→ Open http://localhost:3000 → VideoManager dashboard → Edit → Add panel
→ Dashboard JSON lives at `monitoring/grafana/dashboards/videomanager.json`

### I want to scale this for multiple users
→ [backend/FLOWS.md](backend/FLOWS.md) — "Scaling Guide" section

### I want to change the port nginx listens on
→ `docker-compose.yml` → `nginx.ports`

### I want to change the videos folder
→ `docker-compose.yml` → `backend.volumes` + `nginx.volumes` + `backend.environment.VIDEOS_DIR`
