from scenefoundry.storage.animations import AnimationRecord
from scenefoundry.storage.previews import PreviewRecord
import os
from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from google.cloud import firestore
from pydantic import BaseModel

from scenefoundry.domain.scene import SceneSpec

router = APIRouter(prefix="/v1/projects", tags=["projects"])
ResourceId = Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{1,64}$")]


def get_db() -> Iterator[firestore.Client]:
    db = firestore.Client(project=os.environ["GOOGLE_CLOUD_PROJECT"])
    try:
        yield db
    finally:
        db.close()


Database = Annotated[firestore.Client, Depends(get_db)]


class BudgetSummary(BaseModel):
    allowance_micro_usd: int
    accounted_micro_usd: int
    reserved_micro_usd: int
    available_micro_usd: int


@router.get("/{project_id}/budget")
def read_budget(project_id: ResourceId, db: Database) -> BudgetSummary:
    snapshot = db.document(
        "projects", project_id, "budget", "current"
    ).get(timeout=15)
    if not snapshot.exists:
        raise HTTPException(status_code=404, detail="Project budget not found.")

    data = snapshot.to_dict()
    return BudgetSummary(
        allowance_micro_usd=data["allowance_micro_usd"],
        accounted_micro_usd=data["accounted_micro_usd"],
        reserved_micro_usd=data["reserved_micro_usd"],
        available_micro_usd=(
            data["allowance_micro_usd"]
            - data["accounted_micro_usd"]
            - data["reserved_micro_usd"]
        ),
    )


@router.get("/{project_id}/attempts/{attempt_id}/scene")
def read_scene(
    project_id: ResourceId,
    attempt_id: ResourceId,
    db: Database,
) -> SceneSpec:
    attempt = db.document("projects", project_id, "attempts", attempt_id)
    snapshot = attempt.get(timeout=15)
    if not snapshot.exists:
        raise HTTPException(status_code=404, detail="Attempt not found.")
    if snapshot.get("status") != "succeeded":
        raise HTTPException(status_code=409, detail="Scene is not ready.")

    response = attempt.collection("responses").document("final").get(timeout=15)
    if not response.exists:
        raise HTTPException(status_code=409, detail="Scene response is unavailable.")

    return SceneSpec.model_validate_json(response.get("text"))

@router.get("/{project_id}/attempts/{attempt_id}/previews")
def list_previews(
    project_id: ResourceId,
    attempt_id: ResourceId,
    db: Database,
) -> list[PreviewRecord]:
    attempt = db.document("projects", project_id, "attempts", attempt_id)
    if not attempt.get(timeout=15).exists:
        raise HTTPException(404, "Attempt not found.")

    query = (
        attempt.collection("previews")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(50)
    )
    previews = []
    for snapshot in query.stream(timeout=15):
        record = snapshot.to_dict()
        record.pop("created_at", None)
        previews.append(PreviewRecord.model_validate(record))
    return previews

@router.get("/{project_id}/attempts/{attempt_id}/animations")
def list_animations(
    project_id: ResourceId,
    attempt_id: ResourceId,
    db: Database,
) -> list[AnimationRecord]:
    attempt = db.document("projects", project_id, "attempts", attempt_id)
    if not attempt.get(timeout=15).exists:
        raise HTTPException(404, "Attempt not found.")

    query = (
        attempt.collection("animations")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(50)
    )
    animations = []
    for snapshot in query.stream(timeout=15):
        record = snapshot.to_dict()
        record.pop("created_at", None)
        animations.append(AnimationRecord.model_validate(record))
    return animations
