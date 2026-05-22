from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from config import VIDEOS_DIR
from services.processor import PRESETS, process_video

router = APIRouter()


class ProcessRequest(BaseModel):
    filename: str
    preset: str = "boost_2x"
    overwrite: bool = False


@router.get("/presets")
async def list_presets():
    return list(PRESETS.keys())


@router.post("/")
async def run_process(req: ProcessRequest):
    input_path = (Path(VIDEOS_DIR) / req.filename).resolve()
    videos_root = Path(VIDEOS_DIR).resolve()

    if not input_path.is_relative_to(videos_root):
        raise HTTPException(400, "Invalid filename")
    if not input_path.exists():
        raise HTTPException(404, "File not found")
    if req.preset not in PRESETS:
        raise HTTPException(400, f"Unknown preset. Available: {list(PRESETS.keys())}")

    try:
        out_name = await process_video(req.filename, req.preset, req.overwrite)
    except RuntimeError as e:
        raise HTTPException(500, f"FFmpeg error: {e}")

    return {"filename": out_name}
