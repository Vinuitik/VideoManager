import pytest
from unittest.mock import patch, MagicMock
import state


def test_start_download_returns_job_id(client):
    # Patch _run_download so no actual yt-dlp call happens
    with patch("routers.download_poll._run_download"):
        r = client.post("/api/v1/download", json={"url": "https://youtube.com/watch?v=test"})

    assert r.status_code == 200
    body = r.json()
    assert "job_id" in body
    assert len(body["job_id"]) == 36  # UUID4 format


def test_poll_job_queued(client):
    with patch("routers.download_poll._run_download"):
        start = client.post("/api/v1/download", json={"url": "https://youtube.com/watch?v=x"})
    job_id = start.json()["job_id"]

    r = client.get(f"/api/v1/jobs/{job_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["job_id"] == job_id
    assert body["status"] in ("queued", "downloading", "done")


def test_poll_missing_job_returns_404(client):
    r = client.get("/api/v1/jobs/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_job_reflects_progress(client):
    # Directly write a job into state to test the poll endpoint in isolation
    job = state.new_job("https://example.com")
    job.status = "downloading"
    job.progress = 47.0
    job.speed = "1.5MB/s"

    r = client.get(f"/api/v1/jobs/{job.job_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["progress"] == 47.0
    assert body["speed"] == "1.5MB/s"
