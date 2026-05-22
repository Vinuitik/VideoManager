# VideoManager

Personal yt-dlp frontend. Paste a URL, download a video, boost volume with FFmpeg — no terminal required.

---

## Architecture

```
Browser
  └── nginx :80
        ├── /          → React SPA (compiled static files)
        └── /api/*     → FastAPI backend :8000
                            ├── yt-dlp  (download)
                            └── ffmpeg  (post-process)
                            └── /videos (volume mount → C:\Users\ACER\Desktop\YT-Videos)
```

**Containers (docker-compose)**

| Service   | Role                                      |
|-----------|-------------------------------------------|
| `backend` | FastAPI, wraps yt-dlp + ffmpeg            |
| `nginx`   | Serves compiled React + proxies `/api/*`  |

---

## FLOWS

### Download Flow

```
User pastes URL → POST /api/download
  → backend validates URL
  → yt-dlp.download([url], opts)
  → file written to /videos/
  → response: { filename, title, duration }
```

To change download options (format, quality): `backend/services/downloader.py → ydl_opts`

### List / CRUD Flow

```
Page load → GET /api/videos
  → backend reads /videos/ directory
  → returns [{name, size, modified_at}]

Delete → DELETE /api/videos/{filename}
  → backend unlinks /videos/{filename}
```

To change the watched folder: `VIDEOS_DIR` env var (default `/videos`)

### FFmpeg Post-Process Flow

```
User selects video + action (e.g. boost volume) → POST /api/process
  → backend runs: ffmpeg -i input.mp4 -af "volume=2.0" output.mp4
  → overwrites or saves as new file
  → response: { filename }
```

To change ffmpeg filters or presets: `backend/services/processor.py → PRESETS`

### React + Nginx Build Flow (dev → prod)

```
Dev:   npm run dev  (Vite HMR on :5173, proxies /api → backend:8000)
Prod:  npm run build → dist/
       docker build copies dist/ into nginx image
       nginx serves dist/ as static files
```

To add a new page: `frontend/src/pages/` → register in `frontend/src/App.jsx` router

---

## Change Index

| Thing to change             | Where                                        |
|-----------------------------|----------------------------------------------|
| Download quality/format     | `backend/services/downloader.py` → `ydl_opts`|
| FFmpeg volume presets       | `backend/services/processor.py` → `PRESETS`  |
| Videos storage path         | `VIDEOS_DIR` env var in `docker-compose.yml`  |
| nginx port                  | `docker-compose.yml` → `nginx` ports          |
| API routes                  | `backend/routers/`                            |
| Frontend pages/routes       | `frontend/src/App.jsx`                        |
| Tailwind theme/colors       | `frontend/tailwind.config.js`                 |

---

## Quick Start

```bash
docker compose up --build
# open http://localhost
```

> **Dev mode** (hot reload):
> ```bash
> # terminal 1
> docker compose up backend
> # terminal 2
> cd frontend && npm install && npm run dev
> ```
