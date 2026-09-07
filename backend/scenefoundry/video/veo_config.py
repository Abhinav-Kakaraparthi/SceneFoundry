"""Veo request settings, independent of the director's global endpoint."""

from google.genai import types

VEO_MODEL = "veo-3.1-fast-generate-001"
VEO_LOCATION = "us-central1"


def build_veo_config(
    duration_seconds: int = 4,
    *,
    aspect_ratio: str = "16:9",
) -> types.GenerateVideosConfig:
    """Configure one cinematic clip with native audio."""
    if type(duration_seconds) is not int or duration_seconds not in (4, 6, 8):
        raise ValueError("Veo duration must be an integer: 4, 6, or 8 seconds.")
    if aspect_ratio not in ("9:16", "16:9"):
        raise ValueError("Veo aspect ratio must be 9:16 or 16:9.")

    return types.GenerateVideosConfig(
        number_of_videos=1,
        duration_seconds=duration_seconds,
        aspect_ratio=aspect_ratio,
        resolution="720p",
        generate_audio=True,
        person_generation="allow_adult",
    )
