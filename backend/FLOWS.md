# Backend FLOWS

Files: main.py, config.py, state.py, routers/videos.py, routers/download_poll.py, routers/download_ws.py, routers/process.py, services/downloader.py, services/processor.py, requirements.txt

---

## Video CRUD Flow

```
GET /api/videos/
  → routers/videos.list_videos()
  → Path(VIDEOS_DIR).iterdir()
  → sorted by mtime descending
  → [{name, size, modified_at}]

DELETE /api/videos/{filename}
  → routers/videos.delete_video()
  → path.resolve().is_relative_to(videos_root)  ← path traversal guard
  → path.unlink()
```

To change the watched folder: `VIDEOS_DIR` env var → `config.VIDEOS_DIR`
To add metadata (duration, thumbnail): `routers/videos.list_videos()` — call `yt_dlp.YoutubeDL().extract_info(path, download=False)` per file (slow; cache results)
To debug "file not found" on delete: check that `VIDEOS_DIR` inside the container matches the volume mount in `docker-compose.yml`

---

## Download Flow A — Polling

```
POST /api/v1/download {url}
  → routers/download_poll.start_download_poll()
  → state.new_job(url)          creates Job in state.jobs dict, returns job_id
  → BackgroundTasks.add_task(_run_download, job)
       [FastAPI runs sync tasks in a threadpool — does not block the event loop]
       → services/downloader.download_sync(url, hook)
           → yt_dlp.YoutubeDL(build_ydl_opts(hook)).download([url])
           → hook(d) fires per downloaded chunk:
               d["status"] == "downloading"  →  job.progress / speed / eta  (mutates state.jobs entry)
               d["status"] == "finished"     →  job.status = "done"
  → returns {job_id}   immediately, before download starts

GET /api/v1/jobs/{job_id}
  → routers/download_poll.get_job()
  → plain dict read from state.jobs — no I/O, returns in microseconds
  → {status, progress, speed, eta, filename, error}
```

To change download format/quality: `services/downloader.build_ydl_opts()` → `format` key (yt-dlp format selector string)
To change what fields the poll returns: `routers/download_poll.get_job()` response dict + `_run_download()` hook
To add download to a subfolder (e.g. by channel): `build_ydl_opts()` → `outtmpl` template string
To debug a stuck job: check `state.jobs[job_id].status` — if "queued" forever, the background thread likely threw before the hook fired; add `print` in `_run_download` try/except

---

## Download Flow B — WebSocket

```
WS /api/v2/download
  → routers/download_ws.ws_download()
  → websocket.accept()
  → websocket.receive_json()  →  {url}
  → asyncio.Queue() created   (thread-safe pipe: yt-dlp thread → async WS handler)
  → loop.run_in_executor(None, run)    starts yt-dlp in thread pool
       → build_ydl_opts(hook)  ← services/downloader.py (same opts as Poll)
       → hook(d):
           loop.call_soon_threadsafe(queue.put_nowait, {type, progress, speed, eta})
           None (sentinel) put when thread exits — signals async reader to stop
  → async while loop:
       msg = await queue.get()
       if msg is None: break
       websocket.send_json(msg)
  → websocket.close()
```

Key concept — why `call_soon_threadsafe`: yt-dlp runs in a thread (no async); the WebSocket lives in the event loop. Directly calling `queue.put_nowait` from the thread would be a race condition. `call_soon_threadsafe` schedules the put on the event loop safely.

**Current limitation:** one WebSocket per download. The frontend (`DownloadWS.jsx`) holds one `wsRef` — starting a second download closes the first connection. To fix: add `job_id` to every message, open a single persistent WS in the frontend, demultiplex by `job_id` in `ws.onmessage`.

To change WebSocket message fields: `routers/download_ws.ws_download()` inner `hook()` function
To debug "WebSocket closed immediately": nginx `proxy_read_timeout` in `nginx/nginx.conf` — default is 60s; long downloads need it higher (already set to 3600s)
To debug progress not showing: add `print(d)` inside `hook()` — check that yt-dlp is actually firing the hook (some formats don't report progress)

---

## FFmpeg Post-Process Flow

```
GET /api/process/presets
  → returns list(PRESETS.keys())   use this to populate a dropdown in the UI

POST /api/process {filename, preset, overwrite}
  → routers/process.run_process()
  → path traversal guard
  → services/processor.PRESETS[preset]  →  af_filter string
  → asyncio.create_subprocess_exec("ffmpeg", "-i", input, "-af", filter, output, "-y")
       [proper async subprocess — does not block event loop]
  → await proc.communicate()  →  waits for ffmpeg to finish
  → returns {filename}   (new file if overwrite=False, same file if overwrite=True)
```

To add a new FFmpeg preset: `services/processor.PRESETS` → add `"name": "ffmpeg_audio_filter_string"`
Examples: `"denoise": "afftdn"`, `"speed_2x": "atempo=2.0"`, `"eq_bass": "equalizer=f=100:width_type=o:width=2:g=6"`
To make processing show progress: switch to `ffmpeg -progress pipe:1 -nostats` and parse stderr line by line — same queue pattern as WS download
To debug ffmpeg errors: `routers/process.run_process()` raises `HTTPException(500, stderr)` — the raw ffmpeg error string is returned to the client

---

## Prometheus Metrics Flow

```
Prometheus container (every 15s)
  → GET backend:8000/metrics
  → prometheus-fastapi-instrumentator returns text/plain metrics
  → Prometheus stores as time series

Grafana (on dashboard load / refresh)
  → queries Prometheus via PromQL
  → renders panels: request rate, error rate, latency p50/p95/p99, availability
```

Metrics automatically tracked per endpoint:
- `http_requests_total{handler, method, status}` — count
- `http_request_duration_seconds{handler, method, le}` — histogram (use for latency)
- `http_request_size_bytes` / `http_response_size_bytes` — histograms

To add a custom metric (e.g. active download count):
```python
# in main.py, before Instrumentator()
from prometheus_client import Gauge
active_downloads = Gauge("active_downloads_total", "Downloads currently in progress")
# then in download_poll._run_download(): active_downloads.inc() / active_downloads.dec()
```

To open Grafana: http://localhost:3000 — no login required (anonymous admin)
To debug "no data" in Grafana: check http://localhost:9090/targets — backend must show "UP"

---

## Request Routing (main.py)

| Prefix        | Router                   | Purpose                        |
|---------------|--------------------------|--------------------------------|
| /api/videos   | routers/videos.py        | CRUD — list, delete            |
| /api/v1       | routers/download_poll.py | Download + job poll endpoint   |
| /api/v2       | routers/download_ws.py   | Download via WebSocket         |
| /api/process  | routers/process.py       | FFmpeg post-processing         |
| /api/health   | main.py inline           | Docker health check            |

To add a new API resource: create `routers/myrouter.py`, add `app.include_router(myrouter.router, prefix="/api/x")` in `main.py`

---

## Debugging Guide

| Symptom | Where to look |
|---------|--------------|
| Download never starts | `state.jobs[job_id].status` stuck at "queued" → check `_run_download` exception in logs |
| Progress stuck at 0% | yt-dlp hook not firing → add `print(d)` in `hook()`, check format supports progress |
| WebSocket closes immediately | nginx `proxy_read_timeout` in `nginx/nginx.conf` |
| FFmpeg produces no output | `run_process()` stderr is returned in HTTP 500 response body |
| File not found on delete | `VIDEOS_DIR` env var mismatch with volume mount in `docker-compose.yml` |
| yt-dlp format error | `build_ydl_opts()` → `format` key — check yt-dlp format selector syntax |

---

## Scaling Guide (for reference — not needed now)

Current: in-memory `state.jobs` dict, single process.

To scale to multiple workers:
1. Replace `state.jobs` dict with Redis (`pip install redis`, `redis.StrictRedis().hset(job_id, ...)`)
2. Replace `BackgroundTasks` with a job queue (Celery + Redis broker, or ARQ)
3. Run multiple uvicorn workers (`--workers 4`) or multiple containers
4. nginx already load-balances if you add multiple backend replicas in docker-compose

WebSocket stickiness problem at scale: a WS connection must stay on the same server. Solutions:
- nginx `ip_hash` for sticky routing (simple, imperfect)
- Pub/sub broker (Redis pub/sub) so any server can forward progress to any client

---

## Test Suite

Files: tests/conftest.py, tests/test_unit.py, tests/test_videos.py, tests/test_download_poll.py, tests/test_process.py

**Runner:** `PYTHONPATH=backend pytest backend/tests/ -v`

**Fixture:** `conftest.py` — `client` fixture wraps the FastAPI app in `TestClient` (synchronous, no real HTTP, no running server needed).

### test_unit.py — pure function tests, no I/O, fastest

| Class | What it tests |
|---|---|
| `TestParseProgress` | `parse_progress()` normalises raw yt-dlp hook dicts: correct `%` parsing, `N/A` fallback on malformed input, missing-key safety, filename carried on `finished` status |
| `TestStateNewJob` | `state.new_job()` returns UUID4, registers job in `state.jobs`, sets initial status `"queued"` and `progress=0.0` |
| `TestProcessorPresets` | `services/processor.PRESETS` — all values are non-empty strings, `boost_2x` and `normalize` exist |

### test_videos.py — video CRUD integration

```
client fixture + monkeypatch swaps VIDEOS_DIR → tmp_path (no real disk side-effects)
```

| Test | Covers |
|---|---|
| `test_health` | `GET /api/health` → 200 `{status: ok}` |
| `test_list_videos_empty` | empty folder → `[]` |
| `test_list_videos_returns_files` | file written to tmp_path appears in response |
| `test_delete_video` | `DELETE /api/videos/clip.mp4` → 200, file gone from disk |
| `test_delete_missing_video_returns_404` | 404 on non-existent file |
| `test_delete_path_traversal_blocked` | `../../../etc/passwd` → 400 or 404 (path traversal guard) |

### test_download_poll.py — polling download flow

`_run_download` is patched with `unittest.mock.patch` so no real yt-dlp call happens.

| Test | Covers |
|---|---|
| `test_start_download_returns_job_id` | POST → `{job_id}` is a 36-char UUID4 |
| `test_poll_job_queued` | `GET /api/v1/jobs/{id}` → status in `{queued, downloading, done}` |
| `test_poll_missing_job_returns_404` | unknown job_id → 404 |
| `test_job_reflects_progress` | writes directly into `state.jobs`, polls endpoint, asserts `progress` and `speed` match |

### test_process.py — FFmpeg processing

`process_video` is patched with `AsyncMock` so no real ffmpeg binary needed.

| Test | Covers |
|---|---|
| `test_list_presets` | `GET /api/process/presets` → `boost_2x` and `normalize` present |
| `test_process_missing_file_returns_404` | non-existent file → 404 |
| `test_process_unknown_preset_returns_400` | bad preset name → 400 |
| `test_process_calls_ffmpeg` | mocked `process_video` → 200, filename in response |

To add a test for a new router: create `tests/test_myrouter.py`, import and use the `client` fixture from conftest — no other setup needed.
To test a new pure function: add to `test_unit.py` — no fixture, no patching.
To debug a test that patches the wrong module: the patch path must match where the name is *used*, not where it is defined (e.g. `routers.process.process_video`, not `services.processor.process_video`).

---

## Change Index

| Thing to change              | Where                                              |
|------------------------------|----------------------------------------------------|
| Videos folder path           | `VIDEOS_DIR` env var → `config.VIDEOS_DIR`         |
| Download format / quality    | `services/downloader.build_ydl_opts()` → `format`  |
| yt-dlp output filename/path  | `services/downloader.build_ydl_opts()` → `outtmpl`  |
| Progress fields (poll)       | `routers/download_poll._run_download()` hook + `get_job()` |
| Progress fields (WebSocket)  | `routers/download_ws.ws_download()` inner `hook()` |
| In-memory store → Redis      | `state.py` → swap `jobs` dict for Redis client     |
| FFmpeg presets               | `services/processor.PRESETS`                       |
| API route prefixes           | `main.py` → `app.include_router(..., prefix=...)`  |
| Python version / OS packages | `backend/Dockerfile`                               |
| nginx WS timeout             | `nginx/nginx.conf` → `proxy_read_timeout`          |
| Prometheus scrape interval   | `monitoring/prometheus.yml` → `scrape_interval`    |
| Grafana dashboard panels     | `monitoring/grafana/dashboards/videomanager.json`  |
| Python dependencies          | `backend/requirements.txt`                        |
