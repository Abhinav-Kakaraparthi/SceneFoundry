"""Verify local Veo media before publishing it as a playable result."""

import json
import subprocess
from fractions import Fraction
from pathlib import Path


def verify_veo_mp4(
    video_path: Path,
    *,
    ffprobe: str,
    duration_seconds: int,
) -> dict:
    """Require one 720p/24fps video stream, expected frames, and audio."""
    if type(duration_seconds) is not int or duration_seconds not in (4, 6, 8):
        raise ValueError("Expected duration must be 4, 6, or 8 seconds.")
    if not video_path.is_file():
        raise ValueError("Video file does not exist.")

    process = subprocess.run(
        [
            ffprobe,
            "-v", "error",
            "-count_frames",
            "-show_streams",
            "-show_format",
            "-of", "json",
            "-i", str(video_path.resolve()),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    metadata = json.loads(process.stdout)
    streams = metadata.get("streams", [])
    videos = [stream for stream in streams if stream.get("codec_type") == "video"]
    audios = [stream for stream in streams if stream.get("codec_type") == "audio"]

    if len(videos) != 1 or not audios:
        raise ValueError("Expected one video stream and generated audio.")

    video = videos[0]
    if (video.get("width"), video.get("height")) != (1280, 720):
        raise ValueError("Expected 1280x720 video.")

    try:
        fps = Fraction(video["avg_frame_rate"])
        frames = int(video["nb_read_frames"])
        duration = Fraction(video["duration"])
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
        raise ValueError("Video timing metadata is missing or invalid.") from error

    if fps != 24 or frames != duration_seconds * 24:
        raise ValueError("Video frame rate or frame count differs from the request.")
    if abs(duration - duration_seconds) > Fraction(1, 24):
        raise ValueError("Video duration differs from the request.")

    formats = metadata.get("format", {}).get("format_name", "").split(",")
    if "mp4" not in formats:
        raise ValueError("Expected an MP4 container.")
    return metadata
