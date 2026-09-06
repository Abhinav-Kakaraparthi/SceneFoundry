"""Advance existing video jobs through polling and completion."""

import logging
import os
import shutil
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path as ApiPath
from google.cloud import firestore

from scenefoundry.api.projects import get_db
from scenefoundry.video.completion import complete_veo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/veo/projects", tags=["video"])
StudioId = Annotated[str, ApiPath(pattern=r"^[A-Za-z0-9_-]{1,64}$")]
AttemptId = Annotated[str, ApiPath(pattern=r"^[0-9a-f]{32}$")]


def find_ffprobe() -> str:
    executable = shutil.which("ffprobe")
    if executable:
        return executable

    local_data = os.environ.get("LOCALAPPDATA")
    if local_data:
        packages = Path(local_data) / "Microsoft" / "WinGet" / "Packages"
        candidates = sorted(packages.glob("Gyan.FFmpeg_*/**/bin/ffprobe.exe"))
        if candidates:
            return str(candidates[-1])
    raise HTTPException(503, "FFprobe is unavailable on the server.")


@router.post("/{project_id}/videos/{attempt_id}/refresh")
def refresh_video(
    project_id: StudioId,
    attempt_id: AttemptId,
    db: Annotated[firestore.Client, Depends(get_db)],
) -> dict[str, str]:
    attempt = db.document("projects", project_id, "attempts", attempt_id)
    snapshot = attempt.get(timeout=15)
    if not snapshot.exists:
        raise HTTPException(404, "Video attempt not found.")
    if snapshot.to_dict().get("kind") != "veo_video":
        raise HTTPException(422, "Attempt is not a Veo video.")

    try:
        return complete_veo(
            db,
            studio_project_id=project_id,
            attempt_id=attempt_id,
            ffprobe=find_ffprobe(),
        )
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Video completion failed for attempt %s", attempt_id)
        raise HTTPException(
            503,
            "Completion could not finish. Keep this attempt ID. "
            "Checking it again will not submit a new video.",
        ) from error
