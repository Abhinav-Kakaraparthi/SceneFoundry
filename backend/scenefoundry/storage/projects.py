"""Firestore persistence for user-owned productions."""

from google.api_core.exceptions import Conflict
from google.cloud.firestore_v1.base_query import FieldFilter

from scenefoundry.domain.project import ProductionProject


def _project_document(db, project_id: str):
    return db.document("projects", project_id)


def _parse_project(snapshot) -> ProductionProject:
    payload = snapshot.to_dict()
    if payload is None:
        raise ValueError("Production project does not exist.")

    project = ProductionProject.model_validate(payload)
    if project.project_id != snapshot.id:
        raise ValueError(
            "Production project document identity is inconsistent."
        )

    return project


def _validate_existing_project(
    snapshot,
    expected: ProductionProject,
) -> ProductionProject:
    existing = _parse_project(snapshot)

    comparable_fields = (
        "project_id",
        "creation_id",
        "created_by",
        "title",
        "premise",
        "genre",
        "visual_style",
        "aspect_ratio",
        "episode_count",
        "seconds_per_episode",
        "budget_micro_usd",
        "status",
    )

    if any(
        getattr(existing, field) != getattr(expected, field)
        for field in comparable_fields
    ):
        raise ValueError(
            "Project creation identity conflicts with existing data."
        )

    return existing


def save_production_project(
    db,
    *,
    project: ProductionProject,
) -> tuple[bool, ProductionProject]:
    """Atomically create a production and its initial budget."""

    reference = _project_document(db, project.project_id)
    existing_snapshot = reference.get(timeout=15)

    if existing_snapshot.exists:
        existing = _validate_existing_project(
            existing_snapshot,
            project,
        )
        return False, existing

    project_payload = project.model_dump(mode="python")
    budget_payload = {
        "allowance_micro_usd": project.budget_micro_usd,
        "accounted_micro_usd": 0,
        "reserved_micro_usd": 0,
        "created_at": project.created_at,
    }
    budget_reference = db.document(
        "projects",
        project.project_id,
        "budget",
        "current",
    )

    batch = db.batch()
    batch.create(reference, project_payload)
    batch.create(budget_reference, budget_payload)

    try:
        batch.commit()
    except Conflict:
        raced = reference.get(timeout=15)
        if not raced.exists:
            raise

        existing = _validate_existing_project(raced, project)
        return False, existing

    return True, project


def read_production_project(
    db,
    *,
    project_id: str,
    created_by: str,
) -> ProductionProject:
    """Read a project without revealing another user's project."""

    snapshot = _project_document(db, project_id).get(timeout=15)
    if not snapshot.exists:
        raise ValueError("Production project does not exist.")

    project = _parse_project(snapshot)
    if project.created_by != created_by:
        raise ValueError("Production project does not exist.")

    return project


def list_production_projects(
    db,
    *,
    created_by: str,
) -> tuple[ProductionProject, ...]:
    """List the verified user's newest production records."""

    query = (
        db.collection("projects")
        .where(
            filter=FieldFilter(
                "created_by",
                "==",
                created_by,
            )
        )
        .limit(50)
    )
    projects = tuple(
        _parse_project(snapshot)
        for snapshot in query.stream(timeout=15)
    )

    return tuple(
        sorted(
            projects,
            key=lambda project: project.created_at,
            reverse=True,
        )
    )
