"""Immutable video uploads to private Google Cloud Storage."""

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re

from google.api_core.exceptions import PreconditionFailed
from google.cloud import storage

_CONTENT_TYPE = "video/mp4"
_BUCKET_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{1,61}[a-z0-9]")
_PROJECT_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,64}")
_ATTEMPT_PATTERN = re.compile(r"[0-9a-f]{32}")


@dataclass(frozen=True)
class StoredVideo:
    bucket_name: str
    object_name: str
    sha256: str
    size_bytes: int
    generation: int
    created: bool

    @property
    def uri(self) -> str:
        return f"gs://{self.bucket_name}/{self.object_name}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def upload_video(
    client: storage.Client,
    *,
    bucket_name: str,
    studio_project_id: str,
    attempt_id: str,
    source: Path,
) -> StoredVideo:
    """Create an immutable MP4 object; accept an identical retry."""
    if not _BUCKET_PATTERN.fullmatch(bucket_name):
        raise ValueError("Invalid Cloud Storage bucket name.")
    if not _PROJECT_PATTERN.fullmatch(studio_project_id):
        raise ValueError("Invalid studio project ID.")
    if not _ATTEMPT_PATTERN.fullmatch(attempt_id):
        raise ValueError("Invalid video attempt ID.")

    path = Path(source)
    if not path.is_file() or path.suffix.lower() != ".mp4":
        raise ValueError("Expected an existing MP4 source file.")

    size = path.stat().st_size
    if size <= 0:
        raise ValueError("Video source is empty.")

    digest = _sha256(path)
    object_name = (
        f"projects/{studio_project_id}/videos/{attempt_id}/preview.mp4"
    )
    expected_metadata = {
        "sha256": digest,
        "size_bytes": str(size),
        "studio_project_id": studio_project_id,
        "video_attempt_id": attempt_id,
    }

    blob = client.bucket(bucket_name).blob(object_name)
    blob.metadata = expected_metadata

    try:
        blob.upload_from_filename(
            str(path),
            content_type=_CONTENT_TYPE,
            if_generation_match=0,
            checksum="crc32c",
            timeout=120,
        )
        created = True
    except PreconditionFailed:
        created = False

    blob.reload(timeout=30)
    metadata = blob.metadata or {}
    identical = (
        blob.content_type == _CONTENT_TYPE
        and int(blob.size or -1) == size
        and all(
            metadata.get(key) == value
            for key, value in expected_metadata.items()
        )
    )
    if not identical:
        raise ValueError(
            "Cloud object already exists with different content or metadata."
        )
    if blob.generation is None:
        raise RuntimeError("Cloud object has no generation.")

    return StoredVideo(
        bucket_name=bucket_name,
        object_name=object_name,
        sha256=digest,
        size_bytes=size,
        generation=int(blob.generation),
        created=created,
    )
