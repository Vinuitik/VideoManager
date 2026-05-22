"""
Unit tests — pure functions with no I/O, no HTTP, no mocking needed.
These are the fastest tests and should be run first.
"""
import pytest
from services.downloader import parse_progress


class TestParseProgress:
    """parse_progress() normalises raw yt-dlp hook dicts into a consistent shape."""

    def test_downloading_status(self):
        d = {
            "status": "downloading",
            "_percent_str": " 47.3%",
            "_speed_str": "1.5MiB/s",
            "_eta_str": "00:32",
            "filename": "",
        }
        result = parse_progress(d)
        assert result["progress"] == pytest.approx(47.3)
        assert result["speed"] == "1.5MiB/s"
        assert result["eta"] == "00:32"

    def test_malformed_percent_returns_zero(self):
        d = {"status": "downloading", "_percent_str": "N/A", "_speed_str": "", "_eta_str": "", "filename": ""}
        result = parse_progress(d)
        assert result["progress"] == 0.0

    def test_missing_keys_return_defaults(self):
        # yt-dlp sometimes omits keys — must not raise
        result = parse_progress({"status": "downloading"})
        assert result["progress"] == 0.0
        assert result["speed"] == "N/A"
        assert result["eta"] == "N/A"

    def test_finished_status_carries_filename(self):
        d = {"status": "finished", "_percent_str": "100%", "_speed_str": "", "_eta_str": "", "filename": "/videos/clip.mp4"}
        result = parse_progress(d)
        assert result["filename"] == "/videos/clip.mp4"


class TestStateNewJob:
    """state.new_job() creates a Job with a valid UUID and registers it in state.jobs."""

    def test_creates_job_with_uuid(self):
        import state
        job = state.new_job("https://example.com")
        assert len(job.job_id) == 36
        assert "-" in job.job_id

    def test_job_stored_in_state(self):
        import state
        job = state.new_job("https://example.com")
        assert state.jobs[job.job_id] is job

    def test_initial_status_is_queued(self):
        import state
        job = state.new_job("https://example.com")
        assert job.status == "queued"
        assert job.progress == 0.0


class TestProcessorPresets:
    """Verify preset definitions are non-empty strings (catch typos at test time)."""

    def test_all_presets_are_non_empty_strings(self):
        from services.processor import PRESETS
        for name, value in PRESETS.items():
            assert isinstance(value, str) and value, f"preset '{name}' is empty"

    def test_default_presets_exist(self):
        from services.processor import PRESETS
        assert "boost_2x" in PRESETS
        assert "normalize" in PRESETS
