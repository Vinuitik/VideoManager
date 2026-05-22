# Backend FLOWS

Files: main.py, config.py, state.py, routers/videos.py, routers/download_poll.py, routers/download_ws.py, routers/process.py, services/downloader.py, services/processor.py

---

## Video CRUD Flow

```
GET /api/videos
  → videos.list_videos()
  → Path(VIDEOS_DIR).iterdir()
  → [{name, size, modified_at}]  sorted newest-first

DELETE /api/videos/{filename}
  → videos.delete_video()
  → path traversal guard (path.is_relative_to(videos_root))
  → path.unlink()
```

To change watched folder: `VIDEOS_DIR` env var → `config.VIDEOS_DIR`
To add metadata (duration, thumbnail): `routers/videos.list_videos()` — call yt-dlp's `extract_info(download=False)` per file

---

## Download Flow A — Polling

```
POST /api/v1/download {url}
  → download_poll.start_download_poll()
  → state.new_job(url)  →  state.jobs[job_id] = Job(...)
  → BackgroundTasks.add_task(_run_download, job)
       [background thread]
       → download_sync(url, hook)  ← services/downloader.py
           → yt_dlp.YoutubeDL(build_ydl_opts(hook)).download([url])
           → hook(d) called per chunk:
               d["status"] == "downloading"  →  job.progress / speed / eta updated in state.jobs
               d["status"] == "finished"     →  job.status = "done"
  → returns {job_id}

GET /api/v1/jobs/{job_id}
  → download_poll.get_job()
  → reads state.jobs[job_id]  (plain dict read, no I/O)
  → returns {status, progress, speed, eta, filename, error}
```

To change download format/quality: `services/downloader.build_ydl_opts()` → `format` key
To change progress fields returned: `download_poll._run_download()` hook + `get_job()` response dict
To swap in-memory dict for Redis: replace `state.jobs` with a Redis client in `state.py`

---

## Download Flow B — WebSocket

```
WS /api/v2/download
  → ws_download.ws_download()
  → websocket.accept()
  → websocket.receive_json()  →  {url}
  → asyncio.Queue() created  (thread-safe bridge between yt-dlp thread and async WS)
  → loop.run_in_executor(None, run)  [yt-dlp starts in thread pool]
       → build_ydl_opts(hook)  ← services/downloader.py
       → hook(d):
           loop.call_soon_threadsafe(queue.put_nowait, {type, progress, speed, eta})
           sentinel (None) put when thread finishes
  → async while loop: msg = await queue.get()
       → websocket.send_json(msg)  per progress event (sub-second)
       → breaks on sentinel, closes socket
```

Key concept: `loop.call_soon_threadsafe()` is the bridge — yt-dlp runs in a thread
(no async), but the WebSocket lives in the async event loop. This is the standard
pattern for mixing sync libs with async frameworks.

To change WebSocket message shape: `download_ws.ws_download()` inner `hook()` function
To add job_id multiplexing (multiple downloads, one WS): add `job_id` field to each message, route client-side by it

---

## FFmpeg Post-Process Flow

```
GET /api/process/presets
  → returns list(PRESETS.keys())

POST /api/process {filename, preset, overwrite}
  → process.run_process()
  → path traversal guard
  → PRESETS[preset]  →  af_filter string  ← services/processor.PRESETS
  → asyncio.create_subprocess_exec("ffmpeg", "-i", input, "-af", filter, output, "-y")
  → await proc.communicate()
  → returns {filename}
```

To add a new FFmpeg preset: `services/processor.PRESETS` — add `"name": "ffmpeg_filter_string"`
To make processing report progress: switch to `ffmpeg -progress pipe:1` and stream stderr — same pattern as WS download

---

## Request Routing (main.py)

| Prefix         | Router file              | Purpose                  |
|----------------|--------------------------|--------------------------|
| /api/videos    | routers/videos.py        | CRUD — list, delete      |
| /api/v1        | routers/download_poll.py | Download + poll endpoint |
| /api/v2        | routers/download_ws.py   | Download via WebSocket   |
| /api/process   | routers/process.py       | FFmpeg post-processing   |
| /api/health    | main.py                  | Health check for Docker  |

---

## Change Index

| Thing to change              | Where                                              |
|------------------------------|----------------------------------------------------|
| Videos folder path           | `VIDEOS_DIR` env var → `config.VIDEOS_DIR`         |
| Download format / quality    | `services/downloader.build_ydl_opts()` → `format`  |
| Progress fields (poll)       | `routers/download_poll._run_download()` hook        |
| Progress fields (WebSocket)  | `routers/download_ws.ws_download()` hook            |
| In-memory store → Redis      | `state.py` → swap `jobs` dict for Redis client     |
| FFmpeg presets               | `services/processor.PRESETS`                       |
| API route prefixes           | `main.py` → `app.include_router(..., prefix=...)`  |
| Python version / OS packages | `backend/Dockerfile`                               |
