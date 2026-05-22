from pathlib import Path
from fastapi import APIRouter, HTTPException
from config import VIDEOS_DIR

router = APIRouter()


@router.get("/")
async def list_videos():
    path = Path(VIDEOS_DIR)
    if not path.exists():
        return []
    files = []
    for f in sorted(path.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.is_file() and not f.name.startswith("."):
            stat = f.stat()
            files.append({
                "name": f.name,
                "size": stat.st_size,
                "modified_at": stat.st_mtime,
            })
    return files


@router.delete("/{filename}")
async def delete_video(filename: str):
    path = (Path(VIDEOS_DIR) / filename).resolve()
    videos_root = Path(VIDEOS_DIR).resolve()

    # Guard against path traversal
    if not path.is_relative_to(videos_root):
        raise HTTPException(400, "Invalid filename")
    if not path.exists():
        raise HTTPException(404, "File not found")

    path.unlink()
    return {"deleted": filename}
