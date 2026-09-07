"""Firestore persistence for immutable production research."""

import json

from google.api_core.exceptions import AlreadyExists
from google.cloud import firestore

from scenefoundry.domain.research_record import (
    ProductionResearchRecord,
)


def _research_document(
    db,
    *,
    studio_project_id: str,
    research_id: str,
):
    return db.document(
        "projects",
        studio_project_id,
        "research",
        research_id,
    )


def _research_collection(
    db,
    *,
    studio_project_id: str,
):
    return db.collection(
        "projects",
        studio_project_id,
        "research",
    )


def _parse_record(snapshot) -> ProductionResearchRecord:
    payload = snapshot.to_dict()
    if payload is None:
        raise ValueError("Production research does not exist.")

    payload.pop("created_at", None)
    record = ProductionResearchRecord.model_validate_json(
        json.dumps(payload),
    )

    if record.research_id != snapshot.id:
        raise ValueError(
            "Research document identity is inconsistent."
        )

    return record


def find_production_research(
    db,
    *,
    studio_project_id: str,
    research_id: str,
) -> ProductionResearchRecord | None:
    snapshot = _research_document(
        db,
        studio_project_id=studio_project_id,
        research_id=research_id,
    ).get(timeout=15)

    if not snapshot.exists:
        return None

    return _parse_record(snapshot)


def read_production_research(
    db,
    *,
    studio_project_id: str,
    research_id: str,
) -> ProductionResearchRecord:
    record = find_production_research(
        db,
        studio_project_id=studio_project_id,
        research_id=research_id,
    )
    if record is None:
        raise ValueError(
            f"Production research does not exist: {research_id}"
        )
    return record


def save_production_research(
    db,
    *,
    record: ProductionResearchRecord,
) -> bool:
    """Create immutable evidence or accept an identical retry."""

    document = _research_document(
        db,
        studio_project_id=record.studio_project_id,
        research_id=record.research_id,
    )
    existing = document.get(timeout=15)

    if existing.exists:
        if _parse_record(existing) == record:
            return False
        raise ValueError(
            "Research already exists with different evidence."
        )

    payload = record.model_dump(mode="json")
    payload["created_at"] = firestore.SERVER_TIMESTAMP

    try:
        document.create(payload, timeout=15)
    except AlreadyExists:
        raced = document.get(timeout=15)
        if raced.exists and _parse_record(raced) == record:
            return False
        raise ValueError(
            "Research was concurrently created with different evidence."
        )

    return True


def list_production_research(
    db,
    *,
    studio_project_id: str,
    requested_by: str,
) -> tuple[ProductionResearchRecord, ...]:
    records = (
        _parse_record(snapshot)
        for snapshot in _research_collection(
            db,
            studio_project_id=studio_project_id,
        ).stream(timeout=15)
    )

    return tuple(
        sorted(
            (
                record
                for record in records
                if record.requested_by == requested_by
            ),
            key=lambda record: record.research_id,
        )
    )
