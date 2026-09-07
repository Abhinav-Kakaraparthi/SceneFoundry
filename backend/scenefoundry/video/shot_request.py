"""Translate a saved shot into a deterministic Veo request."""

from dataclasses import dataclass

from scenefoundry.domain.production_direction import (
    ProductionDirection,
)
from scenefoundry.domain.scene import SceneSpec

PROMPT_VERSION = "cinematic_shot_v1"
DIRECTION_PROMPT_VERSION = "production_directed_shot_v2"


@dataclass(frozen=True)
class ShotVideoRequest:
    shot_id: str
    prompt: str
    duration_seconds: int
    aspect_ratio: str = "16:9"
    prompt_version: str = PROMPT_VERSION


def _directional_prompt(
    *,
    action: str,
    duration: int,
    direction: ProductionDirection,
) -> str:
    genre = direction.genre.replace("_", " ").title()
    style = direction.visual_style.replace("_", " ").title()
    premise = " ".join(direction.premise.split())[:600]

    return (
        f"Create a {style} {genre} cinematic shot lasting "
        f"{duration} seconds, composed specifically for "
        f"{direction.aspect_ratio}. "
        "Follow the saved shot description exactly, including framing, "
        "subjects, setting, and visible action. Keep movement, materials, "
        "lighting, and color consistent with the selected visual style. "
        f"Maintain continuity with this project premise: {premise}\n\n"
        "Generate appropriate scene ambience and action sounds. "
        "Do not add unrequested dialogue, music, captions, text overlays, "
        "or unrelated actions.\n\n"
        f"Saved shot description:\n{action}"
    )


def build_shot_video_request(
    scene: SceneSpec,
    shot_id: str,
    *,
    direction: ProductionDirection | None = None,
) -> ShotVideoRequest:
    """Preserve shot action and require exact supported timeline timing."""
    shot = next((item for item in scene.shots if item.shot_id == shot_id), None)
    if shot is None:
        raise ValueError("Shot does not exist in the saved scene.")
    if scene.fps != 24:
        raise ValueError("Veo integration currently requires a 24 fps scene.")

    duration, remainder = divmod(shot.frames.frame_count, scene.fps)
    if remainder or duration not in (4, 6, 8):
        raise ValueError("Veo shots must last exactly 4, 6, or 8 seconds.")

    if direction is None:
        prompt = (
            f"Create a photorealistic live-action cinematic shot lasting "
            f"{duration} seconds. Follow the shot description below, "
            "including its framing, subjects, setting, and visible action. "
            "Use natural movement, realistic materials, and coherent "
            "lighting. Keep the key action readable in the composition. "
            "Generate natural scene ambience and action sounds. "
            "Do not add unrequested dialogue, music, captions, or text "
            "overlays.\n\n"
            f"Shot description:\n{shot.action}"
        )
        aspect_ratio = "16:9"
        prompt_version = PROMPT_VERSION
    else:
        prompt = _directional_prompt(
            action=shot.action,
            duration=duration,
            direction=direction,
        )
        aspect_ratio = direction.aspect_ratio
        prompt_version = DIRECTION_PROMPT_VERSION

    if len(prompt) > 4000:
        raise ValueError("Prepared video prompt exceeds 4000 characters.")

    return ShotVideoRequest(
        shot_id=shot.shot_id,
        prompt=prompt,
        duration_seconds=duration,
        aspect_ratio=aspect_ratio,
        prompt_version=prompt_version,
    )
