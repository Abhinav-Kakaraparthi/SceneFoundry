"""Advance an existing Veo attempt without submitting another generation."""

import hashlib
import json
import os

from google.cloud import firestore, storage

from scenefoundry.paths import local_data_root
from scenefoundry.video.cinematic_artifacts import (
    save_cinematic_clip_provenance,
)
from scenefoundry.storage.cloud_media import upload_video
from scenefoundry.storage.veo_previews import (
    CloudVideo,
    VeoPreview,
    save_veo_preview,
)
from scenefoundry.storage.video_settlement import settle_video
from scenefoundry.video.client import create_veo_client
from scenefoundry.video.extraction import extract_veo_mp4
from scenefoundry.video.polling import poll_veo
from scenefoundry.video.receipts import save_veo_result
from scenefoundry.video.verification import verify_veo_mp4


def complete_veo(
    db: firestore.Client,
    *,
    studio_project_id: str,
    attempt_id: str,
    ffprobe: str,
) -> dict[str, str]:
    """Poll once, then checkpoint, account, verify, and publish returned media."""
    import re

    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", studio_project_id):
        raise ValueError("Invalid studio project ID.")
    if not re.fullmatch(r"[0-9a-f]{32}", attempt_id):
        raise ValueError("Invalid video attempt ID.")

    attempt = db.document("projects", studio_project_id, "attempts", attempt_id)
    snapshot = attempt.get(timeout=15)
    if not snapshot.exists:
        raise ValueError("Video attempt does not exist.")
    data = snapshot.to_dict()
    if data.get("kind") != "veo_video":
        raise ValueError("Attempt is not a Veo video.")

    result = {"attempt_id": attempt_id}
    if data.get("status") == "succeeded":
        return result | {"status": "succeeded"}

    source_id = data.get("source_attempt_id")
    revision_id = data.get("source_revision_id")
    shot_id = data.get("source_shot_id")
    if not source_id or not revision_id or not shot_id:
        raise ValueError(
            "Video attempt lacks source shot and revision provenance."
        )

    saved = attempt.collection("provider").document("operation").get(timeout=15)
    if not saved.exists:
        return result | {
            "status": "needs_review",
            "message": "No saved operation. Submission may be incomplete; do not resubmit.",
        }
    operation_name = saved.get("operation_name")

    directory = local_data_root() / "veo" / attempt_id
    receipt_path = directory / "provider_result.json"

    if not receipt_path.exists():
        with create_veo_client(db.project) as client:
            operation = poll_veo(
                client, operation_name, project_id=db.project
            )
        if operation.done is not True:
            return result | {"status": "running"}
        save_veo_result(
            directory, operation, expected_operation_name=operation_name
        )

    receipt_bytes = receipt_path.read_bytes()
    receipt = json.loads(receipt_bytes)
    operation = receipt["operation"]
    if (
        receipt.get("format_version") != 1
        or operation.get("name") != operation_name
        or operation.get("done") is not True
    ):
        raise ValueError("Saved receipt does not match the completed operation.")

    videos = (operation.get("response") or {}).get("generated_videos") or []
    if operation.get("error") is not None or len(videos) != 1:
        return result | {
            "status": "needs_review",
            "message": "Provider result saved; generation requires review.",
        }
    video = videos[0].get("video") or {}
    if not video.get("video_bytes") and not video.get("uri"):
        return result | {
            "status": "needs_review",
            "message": "Provider returned no usable video location or bytes.",
        }

    settle_video(
        db,
        studio_project_id=studio_project_id,
        attempt_id=attempt_id,
        receipt_sha256=hashlib.sha256(receipt_bytes).hexdigest(),
    )
    video_path = extract_veo_mp4(
        directory, expected_operation_name=operation_name
    )
    duration = data["video_config"]["duration_seconds"]
    verify_veo_mp4(
        video_path,
        ffprobe=ffprobe,
        duration_seconds=duration,
        aspect_ratio=data["video_config"]["aspect_ratio"],
    )
    bucket_name = os.environ.get(
        "SCENEFOUNDRY_MEDIA_BUCKET",
        f"{db.project}-media",
    )
    media_client = storage.Client(project=db.project)
    try:
        stored = upload_video(
            media_client,
            bucket_name=bucket_name,
            studio_project_id=studio_project_id,
            attempt_id=attempt_id,
            source=video_path,
        )
    finally:
        media_client.close()

    save_cinematic_clip_provenance(
        db,
        studio_project_id=studio_project_id,
        source_attempt_id=source_id,
        source_revision_id=revision_id,
        shot_id=shot_id,
        video_attempt_id=attempt_id,
        video_sha256=stored.sha256,
        bucket_name=stored.bucket_name,
        object_name=stored.object_name,
        generation=stored.generation,
    )

    save_veo_preview(
        db,
        studio_project_id=studio_project_id,
        preview=VeoPreview(
            source_attempt_id=source_id,
            video_attempt_id=attempt_id,
            shot_id=shot_id,
            model=data["model"],
            fps=24,
            frame_count=duration * 24,
            video_sha256=stored.sha256,
            cloud_video=CloudVideo(
                bucket_name=stored.bucket_name,
                object_name=stored.object_name,
                generation=stored.generation,
                size_bytes=stored.size_bytes,
            ),
            caption="Veo cinematic preview | Audio included | Saved shot prompt",
        ),
    )
    attempt.update({
        "status": "succeeded",
        "completed_at": firestore.SERVER_TIMESTAMP,
        "media_verified": True,
        "video_sha256": stored.sha256,
        "media_bucket": stored.bucket_name,
        "media_object": stored.object_name,
        "media_generation": stored.generation,
        "media_size_bytes": stored.size_bytes,
    }, timeout=15)
    return result | {"status": "succeeded"}
