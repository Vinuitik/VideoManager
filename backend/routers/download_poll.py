"""
Version A — Polling.

Client POSTs a URL, gets a job_id back immediately.
yt-dlp runs in a background thread and writes progress into state.jobs.
Client polls GET /api/v1/jobs/{job_id} as often as it likes.

At scale this pattern is replaced by: Redis for the state store + a
proper job queue (Celery / RQ / ARQ) for the background work.
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
import state
from services.downloader import download_sync, parse_progress

router = APIRouter()


class DownloadRequest(BaseModel):
    url: str


def _run_download(job: state.Job) -> None:
    """Runs in a background thread. Updates job in-place so polls see live data."""
    def hook(d: dict) -> None:
        p = parse_progress(d)
        if d["status"] == "downloading":
            job.status = "downloading"
            job.progress = p["progress"]
            job.speed = p["speed"]
            job.eta = p["eta"]
        elif d["status"] == "finished":
            job.status = "done"
            job.progress = 100.0
            job.filename = p["filename"]

    try:
        filename = download_sync(job.url, hook)
        job.filename = filename
        job.status = "done"
        job.progress = 100.0
    except Exception as e:
        job.status = "error"
        job.error = str(e)


@router.post("/download")
async def start_download_poll(req: DownloadRequest, background_tasks: BackgroundTasks):
    job = state.new_job(req.url)
    # FastAPI runs sync background tasks in a threadpool — won't block the event loop
    background_tasks.add_task(_run_download, job)
    return {"job_id": job.job_id}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    job = state.jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return {
        "job_id": job.job_id,
        "status": job.status,
        "progress": job.progress,
        "speed": job.speed,
        "eta": job.eta,
        "filename": job.filename,
        "error": job.error,
    }
