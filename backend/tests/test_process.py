import pytest
from unittest.mock import patch, AsyncMock


def test_list_presets(client):
    r = client.get("/api/process/presets")
    assert r.status_code == 200
    presets = r.json()
    assert "boost_2x" in presets
    assert "normalize" in presets


def test_process_missing_file_returns_404(client, tmp_path, monkeypatch):
    import routers.process as pr
    monkeypatch.setattr(pr, "VIDEOS_DIR", str(tmp_path))

    r = client.post("/api/process/", json={"filename": "ghost.mp4", "preset": "boost_2x"})
    assert r.status_code == 404


def test_process_unknown_preset_returns_400(client, tmp_path, monkeypatch):
    import routers.process as pr
    monkeypatch.setattr(pr, "VIDEOS_DIR", str(tmp_path))
    (tmp_path / "clip.mp4").write_bytes(b"data")

    r = client.post("/api/process/", json={"filename": "clip.mp4", "preset": "nonexistent"})
    assert r.status_code == 400


def test_process_calls_ffmpeg(client, tmp_path, monkeypatch):
    import routers.process as pr
    monkeypatch.setattr(pr, "VIDEOS_DIR", str(tmp_path))
    (tmp_path / "clip.mp4").write_bytes(b"data")

    # Mock the processor so no real ffmpeg binary needed in CI
    with patch("routers.process.process_video", new_callable=AsyncMock, return_value="clip_processed.mp4"):
        r = client.post("/api/process/", json={"filename": "clip.mp4", "preset": "boost_2x"})

    assert r.status_code == 200
    assert r.json()["filename"] == "clip_processed.mp4"
