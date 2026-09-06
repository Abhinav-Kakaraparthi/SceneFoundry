"""Atomic local checkpoints for completed Veo responses."""

import base64
import json
import os
import tempfile
from pathlib import Path

from google.genai import types


def _encode_bytes(value: object) -> dict[str, str]:
    if isinstance(value, bytes):
        return {"base64": base64.b64encode(value).decode("ascii")}
    raise TypeError(f"Unsupported receipt value: {type(value).__name__}")


def save_veo_result(
    directory: Path,
    operation: types.GenerateVideosOperation,
    *,
    expected_operation_name: str,
) -> bool:
    """Save a terminal response once; return False for identical content."""
    if not expected_operation_name or operation.name != expected_operation_name:
        raise ValueError("Operation does not match the expected submission.")
    if operation.done is not True:
        raise ValueError("Only completed operations can be checkpointed.")

    payload = json.dumps(
        {
            "format_version": 1,
            "operation": operation.model_dump(mode="python", exclude_none=True),
        },
        default=_encode_bytes,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")

    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / "provider_result.json"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".receipt-", dir=directory
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError:
            if destination.read_bytes() == payload:
                return False
            raise ValueError("A different provider result is already saved.") from None
        return True
    finally:
        temporary.unlink(missing_ok=True)
