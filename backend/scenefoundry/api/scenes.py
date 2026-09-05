from fastapi import APIRouter
from pydantic import BaseModel

from scenefoundry.domain.scene import SceneSpec

router = APIRouter(prefix="/v1/scenes", tags=["scenes"])


class SceneValidation(BaseModel):
    scene_id: str
    shot_count: int
    frame_count: int
    fps: int
    duration_seconds: float


@router.post("/validate", response_model=SceneValidation)
async def validate_scene(scene: SceneSpec) -> SceneValidation:
    return SceneValidation(
        scene_id=scene.scene_id,
        shot_count=len(scene.shots),
        frame_count=scene.frame_count,
        fps=scene.fps,
        duration_seconds=scene.frame_count / scene.fps,
    )