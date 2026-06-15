"""
VideoManager — LITE downloader entrypoint.

The "salvageable" subset of VideoManager: a standalone yt-dlp download API that
reuses the existing routers + services UNCHANGED, but drops the heavy half of the
project (Ollama, ChromaDB/RAG, Playwright agent, FastMCP, Prometheus). Built for
the ObsidianOptimizer browser extension's "Download a resource" button — queue a
YouTube / MIT OCW playlist / uni lecture for offline viewing without standing up
the whole AI stack.

Run:  cd backend && uvicorn lite:app --port 8000
Docker: see ../docker-compose.lite.yml (Dockerfile.lite, no Playwright layer).

What it reuses (zero rewrite):
  routers/videos.py        — GET/DELETE the downloaded files
  routers/download_poll.py — POST /api/v1/download + GET /api/v1/jobs/{id} (+ /subs)
  routers/download_ws.py   — WS /api/v2/download (live progress)
  routers/process.py       — optional ffmpeg audio presets
  services/downloader.py   — build_ydl_opts / download_sync / fetch_subs / parse_progress
  state.py                 — in-memory job store

What it deliberately omits: the agent ReAct loop (auth/scrape escalation), RAG,
MCP server, credentials vault, metrics. yt-dlp alone handles YouTube/OCW/most uni
portals; for sites that need login or JS-scraping, run the FULL stack (main.py).
Agent escalation is disabled here via AGENT_ESCALATION=0 (see download_poll.py).
"""
import os

os.environ.setdefault("AGENT_ESCALATION", "0")  # lite = yt-dlp only, never load the agent

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import videos, download_poll, download_ws, process

app = FastAPI(title="VideoManager Lite (downloader)")

# Open CORS: the only callers are the browser extension's background worker and the
# ObsidianOptimizer backend — both trusted, and this binds to localhost by default.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(videos.router,        prefix="/api/videos", tags=["videos"])
app.include_router(download_poll.router, prefix="/api/v1",      tags=["poll"])
app.include_router(download_ws.router,   prefix="/api/v2",      tags=["websocket"])
app.include_router(process.router,       prefix="/api/process", tags=["process"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "mode": "lite"}
