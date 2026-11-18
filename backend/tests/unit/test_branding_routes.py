"""
Unit tests for branding API routes.
"""

import subprocess
from pathlib import Path
import pytest
from sqlalchemy import select

from src.models import User


@pytest.fixture
def outro_5s(tmp_path):
    path = tmp_path / "outro_4s.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=size=640x360:rate=25",
            "-t", "4",
            "-c:v", "libx264",
            str(path),
        ],
        check=True,
        capture_output=True,
    )
    return path


@pytest.fixture
def outro_7s(tmp_path):
    path = tmp_path / "outro_7s.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=size=640x360:rate=25",
            "-t", "7",
            "-c:v", "libx264",
            str(path),
        ],
        check=True,
        capture_output=True,
    )
    return path


@pytest.fixture
def bgm_audio(tmp_path):
    path = tmp_path / "music.mp3"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "sine=frequency=220:duration=3",
            "-t", "3",
            "-c:a", "libmp3lame",
            str(path),
        ],
        check=True,
        capture_output=True,
    )
    return path


@pytest.mark.asyncio
async def test_branding_endpoints(client, auth_headers, db_session, outro_5s, outro_7s, bgm_audio):
    # Ensure test user exists in db
    user_id = auth_headers["x-supoclip-user-id"]
    existing = await db_session.execute(select(User).where(User.id == user_id))
    if not existing.scalar_one_or_none():
        user = User(
            id=user_id,
            name="Test User",
            email=f"{user_id}@example.com",
            create_settings={},
        )
        db_session.add(user)
        await db_session.commit()

    # 1. Reject outro > 5s
    with open(outro_7s, "rb") as f:
        res_reject = await client.post(
            "/branding/outro-video",
            headers=auth_headers,
            files={"file": ("outro_7s.mp4", f, "video/mp4")},
        )
    assert res_reject.status_code == 400
    assert "5 seconds or less" in res_reject.json()["detail"]

    # 2. Accept outro <= 5s
    with open(outro_5s, "rb") as f:
        res_accept = await client.post(
            "/branding/outro-video",
            headers=auth_headers,
            files={"file": ("outro_4s.mp4", f, "video/mp4")},
        )
    assert res_accept.status_code == 200
    data = res_accept.json()
    assert data["success"] is True
    assert data["outroVideo"]["duration"] <= 5.05

    # 3. Accept background music
    with open(bgm_audio, "rb") as f:
        res_bgm = await client.post(
            "/branding/background-music",
            headers=auth_headers,
            files={"file": ("music.mp3", f, "audio/mpeg")},
        )
    assert res_bgm.status_code == 200
    bgm_data = res_bgm.json()
    assert bgm_data["success"] is True
    assert bgm_data["backgroundMusic"]["filename"] == "music.mp3"

    # 4. Get branding
    res_get = await client.get("/branding", headers=auth_headers)
    assert res_get.status_code == 200
    branding = res_get.json()
    assert branding["backgroundMusic"] is not None
    assert branding["outroVideo"] is not None

    # 5. Get file preview
    res_file = await client.get("/branding/file?type=bgm", headers=auth_headers)
    assert res_file.status_code == 200

    # 6. Delete outro
    res_del_outro = await client.delete("/branding/outro-video", headers=auth_headers)
    assert res_del_outro.status_code == 200

    # 7. Delete bgm
    res_del_bgm = await client.delete("/branding/background-music", headers=auth_headers)
    assert res_del_bgm.status_code == 200
