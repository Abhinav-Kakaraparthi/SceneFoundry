"""Serve generation-pinned videos from private Cloud Storage."""

from collections.abc import Iterator
import os
import re
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Path as ApiPath
from fastapi.responses import Response
from google.api_core.exceptions import NotFound, PreconditionFailed
from google.cloud import storage
from pydantic import ValidationError

from scenefoundry.api.projects import Database
from scenefoundry.storage.veo_previews import CloudVideo

router = APIRouter(prefix="/v1/projects", tags=["video"])
StudioId = Annotated[str, ApiPath(pattern=r"^[A-Za-z0-9_-]{1,64}$")]
AttemptId = Annotated[str, ApiPath(pattern=r"^[0-9a-f]{32}$")]


def get_storage() -> Iterator[storage.Client]:
    client = storage.Client(project=os.environ["GOOGLE_CLOUD_PROJECT"])
    try:
        yield client
    finally:
        client.close()


StorageClient = Annotated[storage.Client, Depends(get_storage)]


def _range_error(size: int) -> HTTPException:
    return HTTPException(
        status_code=416,
        detail="Requested byte range is not satisfiable.",
        headers={"Content-Range": f"bytes */{size}"},
    )


def _parse_range(value: str | None, size: int) -> tuple[int, int] | None:
    if value is None:
        return None

    match = re.fullmatch(r"bytes=(\d*)-(\d*)", value.strip())
    if not match or not any(match.groups()):
        raise _range_error(size)

    start_text, end_text = match.groups()
    if not start_text:
        suffix = int(end_text)
        if suffix <= 0:
            raise _range_error(size)
        return max(size - suffix, 0), size - 1

    start = int(start_text)
    if start >= size:
        raise _range_error(size)

    end = size - 1 if not end_text else min(int(end_text), size - 1)
    if end < start:
        raise _range_error(size)
    return start, end


@router.get("/{project_id}/videos/{attempt_id}/content")
def read_cloud_video(
    project_id: StudioId,
    attempt_id: AttemptId,
    db: Database,
    gcs: StorageClient,
    range_header: Annotated[str | None, Header(alias="Range")] = None,
) -> Response:
    snapshot = db.document(
        "projects", project_id, "attempts", attempt_id
    ).get(timeout=15)
    if not snapshot.exists:
        raise HTTPException(404, "Video attempt not found.")

    data = snapshot.to_dict()
    if data.get("kind") != "veo_video":
        raise HTTPException(422, "Attempt is not a Veo video.")
    if data.get("status") != "succeeded":
        raise HTTPException(409, "Video is not ready.")

    try:
        media = CloudVideo(
            bucket_name=data["media_bucket"],
            object_name=data["media_object"],
            generation=data["media_generation"],
            size_bytes=data["media_size_bytes"],
        )
    except (KeyError, TypeError, ValidationError) as error:
        raise HTTPException(
            409,
            "Video has not been published to Cloud Storage.",
        ) from error

    expected_object = (
        f"projects/{project_id}/videos/{attempt_id}/preview.mp4"
    )
    if media.object_name != expected_object:
        raise HTTPException(409, "Stored video identity is inconsistent.")

    digest = data.get("video_sha256")
    if not isinstance(digest, str) or not re.fullmatch(
        r"[0-9a-f]{64}", digest
    ):
        raise HTTPException(409, "Stored video digest is invalid.")

    selected = _parse_range(range_header, media.size_bytes)
    download_options: dict[str, object] = {
        "if_generation_match": media.generation,
        "timeout": 60,
        "checksum": None if selected else "crc32c",
    }
    if selected:
        download_options["start"], download_options["end"] = selected

    blob = gcs.bucket(media.bucket_name).blob(
        media.object_name,
        generation=media.generation,
    )
    try:
        payload = blob.download_as_bytes(**download_options)
    except NotFound as error:
        raise HTTPException(404, "Stored video object was not found.") from error
    except PreconditionFailed as error:
        raise HTTPException(
            409,
            "Stored video generation no longer matches its record.",
        ) from error

    expected_size = (
        selected[1] - selected[0] + 1
        if selected
        else media.size_bytes
    )
    if len(payload) != expected_size:
        raise HTTPException(502, "Cloud Storage returned incomplete media.")

    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "private, max-age=3600",
        "Content-Length": str(len(payload)),
        "ETag": f'"{digest}"',
    }
    status = 200
    if selected:
        start, end = selected
        status = 206
        headers["Content-Range"] = (
            f"bytes {start}-{end}/{media.size_bytes}"
        )

    return Response(
        content=payload,
        status_code=status,
        media_type="video/mp4",
        headers=headers,
    )
