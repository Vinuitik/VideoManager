from typing import Callable
import yt_dlp
from config import VIDEOS_DIR


def build_ydl_opts(progress_hook: Callable | None) -> dict:
    opts = {
        "outtmpl": f"{VIDEOS_DIR}/%(title)s.%(ext)s",
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
    }
    if progress_hook is not None:
        opts["progress_hooks"] = [progress_hook]
    return opts


def _parse_percent(raw: str) -> float:
    try:
        return float(raw.strip().replace("%", ""))
    except (ValueError, AttributeError):
        return 0.0


def download_sync(url: str, progress_hook: Callable) -> str:
    opts = build_ydl_opts(progress_hook)
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)


def parse_progress(d: dict) -> dict:
    """Normalise a yt-dlp progress hook dict into a consistent shape."""
    return {
        "progress": _parse_percent(d.get("_percent_str", "0%")),
        "speed": d.get("_speed_str", "N/A").strip(),
        "eta": d.get("_eta_str", "N/A").strip(),
        "filename": d.get("filename", ""),
    }
