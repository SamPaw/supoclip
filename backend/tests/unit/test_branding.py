"""
Unit tests for branding module (background music and outro).
"""

import subprocess
import tempfile
from pathlib import Path
import pytest

from src.media.branding import (
    apply_background_music,
    append_outro_video,
    ffprobe_video_dimensions,
    ffprobe_media_duration,
)


@pytest.fixture
def sample_media():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        clip = p / "clip.mp4"
        outro = p / "outro.mp4"
        bgm = p / "music.mp3"

        # 3s clip
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "testsrc=size=1080x1920:rate=30",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
                "-t", "3",
                "-c:v", "libx264", "-c:a", "aac",
                str(clip)
            ],
            check=True,
            capture_output=True,
        )

        # 2s outro
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "testsrc=size=1280x720:rate=25",
                "-f", "lavfi", "-i", "sine=frequency=880:duration=2",
                "-t", "2",
                "-c:v", "libx264", "-c:a", "aac",
                str(outro)
            ],
            check=True,
            capture_output=True,
        )

        # 4s music
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "sine=frequency=220:duration=4",
                "-t", "4",
                "-c:a", "libmp3lame",
                str(bgm)
            ],
            check=True,
            capture_output=True,
        )

        yield {"clip": clip, "outro": outro, "bgm": bgm}


def test_ffprobe_helpers(sample_media):
    clip = sample_media["clip"]
    w, h = ffprobe_video_dimensions(clip)
    assert (w, h) == (1080, 1920)

    dur = ffprobe_media_duration(clip)
    assert 2.9 <= dur <= 3.2


def test_apply_background_music(sample_media):
    clip = sample_media["clip"]
    bgm = sample_media["bgm"]

    success = apply_background_music(clip, bgm, volume=0.2)
    assert success is True
    assert clip.exists()
    dur = ffprobe_media_duration(clip)
    assert 2.9 <= dur <= 3.2


def test_append_outro_video(sample_media):
    clip = sample_media["clip"]
    outro = sample_media["outro"]

    success = append_outro_video(clip, outro, max_outro_duration=5.0)
    assert success is True
    assert clip.exists()

    w, h = ffprobe_video_dimensions(clip)
    assert (w, h) == (1080, 1920)

    dur = ffprobe_media_duration(clip)
    # 3s + 2s = ~5s
    assert 4.8 <= dur <= 5.3
