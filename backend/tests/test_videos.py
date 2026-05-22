import pytest
from pathlib import Path


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_list_videos_empty(client, tmp_path, monkeypatch):
    # monkeypatch swaps VIDEOS_DIR in the router module for this test only
    import routers.videos as vr
    monkeypatch.setattr(vr, "VIDEOS_DIR", str(tmp_path))

    r = client.get("/api/videos/")
    assert r.status_code == 200
    assert r.json() == []


def test_list_videos_returns_files(client, tmp_path, monkeypatch):
    import routers.videos as vr
    monkeypatch.setattr(vr, "VIDEOS_DIR", str(tmp_path))

    (tmp_path / "video.mp4").write_bytes(b"x" * 1024)

    r = client.get("/api/videos/")
    assert r.status_code == 200
    names = [v["name"] for v in r.json()]
    assert "video.mp4" in names


def test_delete_video(client, tmp_path, monkeypatch):
    import routers.videos as vr
    monkeypatch.setattr(vr, "VIDEOS_DIR", str(tmp_path))

    f = tmp_path / "clip.mp4"
    f.write_bytes(b"data")

    r = client.delete("/api/videos/clip.mp4")
    assert r.status_code == 200
    assert not f.exists()


def test_delete_missing_video_returns_404(client, tmp_path, monkeypatch):
    import routers.videos as vr
    monkeypatch.setattr(vr, "VIDEOS_DIR", str(tmp_path))

    r = client.delete("/api/videos/ghost.mp4")
    assert r.status_code == 404


def test_delete_path_traversal_blocked(client, tmp_path, monkeypatch):
    import routers.videos as vr
    monkeypatch.setattr(vr, "VIDEOS_DIR", str(tmp_path))

    # An attacker tries to escape the videos dir
    r = client.delete("/api/videos/../../../etc/passwd")
    assert r.status_code in (400, 404)
