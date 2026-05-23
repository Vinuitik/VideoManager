from dataclasses import dataclass, field
from typing import Dict, List, Any
import uuid


@dataclass
class Job:
    job_id: str
    url: str
    status: str = "queued"   # queued | downloading | agent | agent_waiting_input | done | error
    progress: float = 0.0
    speed: str = ""
    eta: str = ""
    filename: str = ""
    error: str = ""
    agent_log: List[dict] = field(default_factory=list)
    agent_input_request: dict = field(default_factory=dict)
    input_response: str = ""
    _input_event: Any = field(default=None, repr=False)   # asyncio.Event, set by agent loop


# In-memory store — simulates what Redis would do at scale
jobs: Dict[str, Job] = {}


def new_job(url: str) -> Job:
    job_id = str(uuid.uuid4())
    job = Job(job_id=job_id, url=url)
    jobs[job_id] = job
    return job
