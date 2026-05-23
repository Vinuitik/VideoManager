import asyncio
import yt_dlp
from services.downloader import build_ydl_opts


async def try_ytdlp(
    url: str,
    extra_opts: dict | None = None,
    cookies_path: str = "",
) -> dict:
    """Attempt a yt-dlp download. Returns {success, filename, error}."""
    result: dict = {"success": False, "filename": "", "error": ""}

    def _run() -> None:
        opts = build_ydl_opts(None)
        if cookies_path:
            opts["cookiefile"] = cookies_path
        if extra_opts:
            opts.update(extra_opts)
        opts["quiet"] = False
        opts["no_warnings"] = False

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                result["success"] = True
                result["filename"] = ydl.prepare_filename(info)
        except Exception as exc:
            result["error"] = str(exc)

    await asyncio.get_event_loop().run_in_executor(None, _run)
    return result
