"""
Branding utilities: background music mixing and outro video concatenation.
"""

import logging
from pathlib import Path
import shutil
import subprocess
from typing import Optional, Tuple

from .ffmpeg import ffprobe_has_audio

logger = logging.getLogger(__name__)


def ffprobe_video_dimensions(video_path: Path) -> Tuple[int, int]:
    """Get width and height of video."""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=s=x:p=0",
            str(video_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
        parts = res.stdout.strip().split("x")
        return int(parts[0]), int(parts[1])
    except Exception as exc:
        logger.warning(f"Could not probe video dimensions for {video_path}: {exc}")
        return 1080, 1920


def ffprobe_media_duration(path: Path) -> float:
    """Get media duration in seconds."""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
        return float(res.stdout.strip())
    except Exception as exc:
        logger.warning(f"Could not probe duration for {path}: {exc}")
        return 0.0


def apply_background_music(
    clip_path: Path,
    bg_music_path: Path,
    volume: float = 0.15,
) -> bool:
    """Mix background music into a clip while keeping dialogue clear.
    
    Loops music if clip is longer than music; cuts music when clip ends.
    Uses video stream copy (-c:v copy) so the operation is near-instantaneous.
    """
    if not clip_path.exists():
        logger.warning(f"Clip not found for background music: {clip_path}")
        return False
    if not bg_music_path.exists():
        logger.warning(f"Background music not found: {bg_music_path}")
        return False

    has_audio = ffprobe_has_audio(clip_path)
    volume_clamped = max(0.01, min(1.0, float(volume)))

    temp_output = clip_path.with_name(f"{clip_path.stem}_bgm.mp4")

    try:
        if has_audio:
            filter_complex = (
                f"[0:a]volume=1.0[main];"
                f"[1:a]volume={volume_clamped}[bg];"
                f"[main][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]"
            )
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                str(clip_path),
                "-stream_loop",
                "-1",
                "-i",
                str(bg_music_path),
                "-filter_complex",
                filter_complex,
                "-map",
                "0:v",
                "-map",
                "[aout]",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                "-movflags",
                "+faststart",
                str(temp_output),
            ]
        else:
            # Video had no audio, use background music directly
            duration = ffprobe_media_duration(clip_path)
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                str(clip_path),
                "-stream_loop",
                "-1",
                "-i",
                str(bg_music_path),
                "-map",
                "0:v",
                "-map",
                "1:a",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-t",
                str(duration),
                "-movflags",
                "+faststart",
                str(temp_output),
            ]

        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if res.returncode != 0:
            logger.error(f"Failed to apply background music: {res.stderr}")
            if temp_output.exists():
                temp_output.unlink(missing_ok=True)
            return False

        # Replace original with new file
        shutil.move(str(temp_output), str(clip_path))
        logger.info(f"Applied background music to {clip_path.name} (volume {volume_clamped:.2f})")
        return True
    except Exception as exc:
        logger.error(f"Error applying background music: {exc}")
        if temp_output.exists():
            temp_output.unlink(missing_ok=True)
        return False


def append_outro_video(
    clip_path: Path,
    outro_path: Path,
    max_outro_duration: float = 5.0,
) -> bool:
    """Append an outro video (max 5s) to the end of a clip.
    
    Scales/letterboxes outro to match clip aspect ratio and guarantees audio sync.
    """
    if not clip_path.exists():
        logger.warning(f"Clip not found for outro: {clip_path}")
        return False
    if not outro_path.exists():
        logger.warning(f"Outro video not found: {outro_path}")
        return False

    width, height = ffprobe_video_dimensions(clip_path)
    outro_dur = ffprobe_media_duration(outro_path)
    if outro_dur <= 0:
        logger.warning(f"Invalid outro duration: {outro_dur}")
        return False

    effective_outro_dur = min(max_outro_duration, outro_dur)
    clip_has_audio = ffprobe_has_audio(clip_path)
    outro_has_audio = ffprobe_has_audio(outro_path)

    temp_output = clip_path.with_name(f"{clip_path.stem}_outro.mp4")

    try:
        inputs = [
            "-i", str(clip_path),
            "-i", str(outro_path),
        ]

        filter_parts = [
            f"[0:v]setsar=1,fps=30[v0]",
            f"[1:v]scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v1]",
        ]

        if clip_has_audio and outro_has_audio:
            filter_parts.append("[0:a]aformat=sample_rates=44100:channel_layouts=stereo[a0]")
            filter_parts.append(f"[1:a]atrim=0:{effective_outro_dur},aformat=sample_rates=44100:channel_layouts=stereo[a1]")
        elif clip_has_audio and not outro_has_audio:
            inputs.extend(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"])
            filter_parts.append("[0:a]aformat=sample_rates=44100:channel_layouts=stereo[a0]")
            filter_parts.append(f"[2:a]atrim=0:{effective_outro_dur},aformat=sample_rates=44100:channel_layouts=stereo[a1]")
        elif not clip_has_audio and outro_has_audio:
            clip_dur = ffprobe_media_duration(clip_path)
            inputs.extend(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"])
            filter_parts.append(f"[2:a]atrim=0:{clip_dur},aformat=sample_rates=44100:channel_layouts=stereo[a0]")
            filter_parts.append(f"[1:a]atrim=0:{effective_outro_dur},aformat=sample_rates=44100:channel_layouts=stereo[a1]")
        else:
            clip_dur = ffprobe_media_duration(clip_path)
            inputs.extend(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"])
            filter_parts.append(f"[2:a]atrim=0:{clip_dur},aformat=sample_rates=44100:channel_layouts=stereo[a0]")
            filter_parts.append(f"[2:a]atrim=0:{effective_outro_dur},aformat=sample_rates=44100:channel_layouts=stereo[a1]")

        filter_parts.append("[v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]")

        cmd = [
            "ffmpeg",
            "-y",
            *inputs,
            "-filter_complex",
            ";".join(filter_parts),
            "-map",
            "[outv]",
            "-map",
            "[outa]",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(temp_output),
        ]

        res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if res.returncode != 0:
            logger.error(f"Failed to append outro video: {res.stderr}")
            if temp_output.exists():
                temp_output.unlink(missing_ok=True)
            return False

        shutil.move(str(temp_output), str(clip_path))
        logger.info(f"Appended outro video ({effective_outro_dur:.1f}s) to {clip_path.name}")
        return True
    except Exception as exc:
        logger.error(f"Error appending outro video: {exc}")
        if temp_output.exists():
            temp_output.unlink(missing_ok=True)
        return False
