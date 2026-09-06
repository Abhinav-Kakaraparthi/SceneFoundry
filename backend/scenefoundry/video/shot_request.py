"""Translate a saved shot into a deterministic Veo request."""

from dataclasses import dataclass

from scenefoundry.domain.scene import SceneSpec

PROMPT_VERSION = "cinematic_shot_v1"


@dataclass(frozen=True)
class ShotVideoRequest:
    shot_id: str
    prompt: str
    duration_seconds: int
    prompt_version: str = PROMPT_VERSION


def build_shot_video_request(
    scene: SceneSpec,
    shot_id: str,
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

    prompt = (
        f"Create a photorealistic live-action cinematic shot lasting {duration} seconds. "
        "Follow the shot description below, including its framing, subjects, "
        "setting, and visible action. Use natural movement, realistic materials, "
        "and coherent lighting. Keep the key action readable in the composition. "
        "Generate natural scene ambience and action sounds. "
        "Do not add unrequested dialogue, music, captions, or text overlays.\n\n"
        f"Shot description:\n{shot.action}"
    )
    return ShotVideoRequest(
        shot_id=shot.shot_id,
        prompt=prompt,
        duration_seconds=duration,
    )
