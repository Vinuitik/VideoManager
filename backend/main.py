from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from routers import videos, download_poll, download_ws, process, credentials
from mcp_tools.server import mcp


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Seed RAG on startup (no-op if already populated)
    try:
        from rag.seeder import seed_if_empty
        await seed_if_empty()
    except Exception as exc:
        print(f"[RAG] Seeder skipped: {exc}")
    yield


app = FastAPI(title="VideoManager API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(videos.router,        prefix="/api/videos",      tags=["videos"])
app.include_router(download_poll.router, prefix="/api/v1",           tags=["poll"])
app.include_router(download_ws.router,   prefix="/api/v2",           tags=["websocket"])
app.include_router(process.router,       prefix="/api/process",      tags=["process"])
app.include_router(credentials.router,   prefix="/api",              tags=["credentials"])

# MCP server — Streamable HTTP at /mcp (Claude Code + future mobile clients)
app.mount("/mcp", mcp.http_app())

# Prometheus metrics — scraped by the Prometheus container
Instrumentator().instrument(app).expose(app)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
