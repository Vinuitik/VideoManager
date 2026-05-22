from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from routers import videos, download_poll, download_ws, process

app = FastAPI(title="VideoManager API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(videos.router,        prefix="/api/videos",  tags=["videos"])
app.include_router(download_poll.router, prefix="/api/v1",       tags=["poll"])
app.include_router(download_ws.router,   prefix="/api/v2",       tags=["websocket"])
app.include_router(process.router,       prefix="/api/process",  tags=["process"])

# Exposes /metrics in Prometheus text format — scraped by the Prometheus container
# Tracks: request count, latency histogram, request/response sizes per endpoint
Instrumentator().instrument(app).expose(app)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
