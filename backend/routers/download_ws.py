"""
Version B — WebSocket.

Client opens WS /api/v2/download, sends {"url": "..."}.
Server streams yt-dlp progress events in real time and closes when done.

One WebSocket per download; multiplexed over a single browser connection
via job_id if multiple downloads run simultaneously.
"""
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import yt_dlp
from config import VIDEOS_DIR
from services.downloader import build_ydl_opts, parse_progress

router = APIRouter()

_SENTINEL = None  # signals the async reader that the thread is done


@router.websocket("/download")
async def ws_download(websocket: WebSocket):
    await websocket.accept()

    try:
        data = await websocket.receive_json()
    except Exception:
        await websocket.close(code=1003)
        return

    url = data.get("url", "").strip()
    if not url:
        await websocket.send_json({"type": "error", "message": "No URL provided"})
        await websocket.close()
        return

    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def hook(d: dict) -> None:
        p = parse_progress(d)
        if d["status"] == "downloading":
            loop.call_soon_threadsafe(queue.put_nowait, {
                "type": "progress",
                "progress": p["progress"],
                "speed": p["speed"],
                "eta": p["eta"],
            })
        elif d["status"] == "finished":
            loop.call_soon_threadsafe(queue.put_nowait, {
                "type": "done",
                "filename": p["filename"],
            })

    def run() -> None:
        opts = build_ydl_opts(hook)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
        except Exception as e:
            loop.call_soon_threadsafe(queue.put_nowait, {
                "type": "error",
                "message": str(e),
            })
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, _SENTINEL)

    loop.run_in_executor(None, run)

    try:
        while True:
            msg = await queue.get()
            if msg is _SENTINEL:
                break
            await websocket.send_json(msg)
    except WebSocketDisconnect:
        pass  # client left early — thread will finish naturally
    finally:
        await websocket.close()
