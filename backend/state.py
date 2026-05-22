from dataclasses import dataclass, field
from typing import Dict
import uuid


@dataclass
class Job:
    job_id: str
    url: str
    status: str = "queued"   # queued | downloading | done | error
    progress: float = 0.0
    speed: str = ""
    eta: str = ""
    filename: str = ""
    error: str = ""


# In-memory store — simulates what Redis would do at scale
jobs: Dict[str, Job] = {}


def new_job(url: str) -> Job:
    job_id = str(uuid.uuid4())
    job = Job(job_id=job_id, url=url)
    jobs[job_id] = job
    return job
