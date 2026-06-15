"""
Version A — Polling with agent escalation.

Client POSTs a URL, gets a job_id back immediately.
Phase 1: yt-dlp runs in executor. On success → done.
Phase 2: on failure, AgentLoop runs async — tries RAG, browser inspection, auth.
Client polls GET /api/v1/jobs/{job_id}; status field shows current phase.

Status values: queued | downloading | agent | agent_waiting_input | done | error
"""
import asyncio
import os
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
import state
from services.downloader import download_sync, fetch_subs, parse_progress

router = APIRouter()

# Agent escalation (RAG + headless browser + auth) is the heavy half of VideoManager.
# Default ON keeps full-stack behaviour identical; the LITE downloader sets
# AGENT_ESCALATION=0 so a yt-dlp failure reports a plain error instead of importing
# the agent (which needs Ollama/Chroma/Playwright that lite intentionally omits).
def _agent_escalation_enabled() -> bool:
    return os.getenv("AGENT_ESCALATION", "1").lower() not in ("0", "false", "no")


class DownloadRequest(BaseModel):
    url: str


class SubsRequest(BaseModel):
    url: str
    lang: str = "en"


class AgentInputResponse(BaseModel):
    value: str


async def _run_download_with_agent(job: state.Job) -> None:
    loop = asyncio.get_event_loop()
    ytdlp_failed = False

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

    def _ytdlp_sync() -> None:
        nonlocal ytdlp_failed
        try:
            filename = download_sync(job.url, hook)
            job.filename = filename
            job.status = "done"
            job.progress = 100.0
        except Exception as exc:
            job.error = str(exc)
            ytdlp_failed = True

    await loop.run_in_executor(None, _ytdlp_sync)

    if ytdlp_failed:
        if not _agent_escalation_enabled():
            job.status = "error"  # lite mode: yt-dlp only, no agent escalation
            return
        try:
            from agent.loop import AgentLoop
            await AgentLoop(job).run()
        except Exception as exc:
            job.status = "error"
            job.error = f"Agent failed: {exc}"


@router.post("/download")
async def start_download_poll(req: DownloadRequest, background_tasks: BackgroundTasks):
    job = state.new_job(req.url)
    background_tasks.add_task(_run_download_with_agent, job)
    return {"job_id": job.job_id}


@router.post("/subs")
async def fetch_subtitles(req: SubsRequest):
    """Captions only, no video download — synchronous (a few seconds).
    Used by the ObsidianOptimizer ingest agent's captions-fast-path."""
    loop = asyncio.get_event_loop()
    try:
        return await loop.run_in_executor(None, fetch_subs, req.url, req.lang)
    except Exception as exc:
        raise HTTPException(422, f"subs unavailable: {exc}")


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
        "agent_log": job.agent_log,
        "agent_input_request": job.agent_input_request,
    }


@router.post("/jobs/{job_id}/input")
async def send_agent_input(job_id: str, body: AgentInputResponse):
    """Provide a response when the agent is waiting for user input (CAPTCHA, MFA, etc.)."""
    job = state.jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != "agent_waiting_input":
        raise HTTPException(400, "Job is not waiting for input")
    job.input_response = body.value
    if job._input_event:
        job._input_event.set()
    return {"status": "received"}
