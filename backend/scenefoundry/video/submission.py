"""Submit a Veo request using a caller-owned regional client."""

from google import genai

from scenefoundry.video.veo_config import VEO_MODEL, build_veo_config


def submit_veo(
    client: genai.Client,
    prompt: str,
    duration_seconds: int = 4,
) -> str:
    """Return the operation name; callers must persist it before polling."""
    if not isinstance(prompt, str):
        raise ValueError("Video prompt must be text.")

    prompt = prompt.strip()
    if not 1 <= len(prompt) <= 4000:
        raise ValueError("Video prompt must contain 1 to 4000 characters.")

    config = build_veo_config(duration_seconds)
    operation = client.models.generate_videos(
        model=VEO_MODEL,
        prompt=prompt,
        config=config,
    )

    name = operation.name
    if not isinstance(name, str) or not name.strip():
        raise RuntimeError(
            "Veo returned no operation name. Submission outcome is unknown; "
            "do not automatically resubmit."
        )
    return name
