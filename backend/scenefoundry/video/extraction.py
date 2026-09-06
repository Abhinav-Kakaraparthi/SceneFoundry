"""Recover an embedded MP4 from an immutable local Veo receipt."""

import base64
import binascii
import json
import os
import tempfile
from pathlib import Path


def extract_veo_mp4(
    directory: Path,
    *,
    expected_operation_name: str,
) -> Path:
    """Extract one embedded video; never fetch or regenerate missing output."""
    receipt = json.loads((directory / "provider_result.json").read_bytes())
    if receipt.get("format_version") != 1:
        raise ValueError("Unsupported receipt format.")

    operation = receipt["operation"]
    if not expected_operation_name or operation.get("name") != expected_operation_name:
        raise ValueError("Receipt does not match the expected operation.")
    if operation.get("done") is not True:
        raise ValueError("Operation has not completed.")
    if operation.get("error") is not None:
        raise ValueError("Provider reported a failure; inspect the saved receipt.")

    response = operation.get("response") or {}
    videos = response.get("generated_videos") or []
    if len(videos) != 1:
        raise ValueError("Expected exactly one generated video.")

    video = videos[0].get("video") or {}
    if video.get("mime_type") != "video/mp4":
        raise ValueError("Expected video/mp4 output.")
    encoded = video.get("video_bytes")
    if not isinstance(encoded, dict) or not isinstance(encoded.get("base64"), str):
        raise ValueError("No embedded video bytes; inspect the saved output URI.")

    try:
        payload = base64.b64decode(encoded["base64"], validate=True)
    except (ValueError, binascii.Error) as error:
        raise ValueError("Invalid Base64 video payload.") from error
    if len(payload) < 12 or payload[4:8] != b"ftyp":
        raise ValueError("Video payload lacks the expected MP4 file header.")

    destination = directory / "preview.mp4"
    descriptor, temporary_name = tempfile.mkstemp(prefix=".video-", dir=directory)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError:
            if destination.read_bytes() != payload:
                raise ValueError("A different preview.mp4 already exists.") from None
        return destination
    finally:
        temporary.unlink(missing_ok=True)
