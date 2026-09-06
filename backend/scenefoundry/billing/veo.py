"""Application estimate for one supported Veo output configuration."""

from google.genai import types

RATE_ID = "veo-3.1-fast_720p_audio_estimate_2026-09-06"
MODEL = "veo-3.1-fast-generate-001"
LOCATION = "us-central1"
MICRO_USD_PER_SECOND = 100_000
SOURCE_URL = (
    "https://cloud.google.com/"
    "gemini-enterprise-agent-platform/generative-ai/pricing"
)


def estimate_veo_micro_usd(
    model: str,
    location: str,
    config: types.GenerateVideosConfig,
) -> int:
    """Estimate one requested clip; this does not settle provider charges."""
    if model != MODEL or location != LOCATION:
        raise ValueError("No Veo rate configured for this model and location.")

    if (
        config.resolution != "720p"
        or config.generate_audio is not True
        or config.number_of_videos != 1
    ):
        raise ValueError("Rate requires one 720p video with audio.")

    duration = config.duration_seconds
    if type(duration) is not int or duration not in (4, 6, 8):
        raise ValueError("Unsupported Veo duration.")

    return duration * MICRO_USD_PER_SECOND
