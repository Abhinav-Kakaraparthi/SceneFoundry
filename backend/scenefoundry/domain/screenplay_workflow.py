"""Server-derived screenplay version creation."""

from pydantic import BaseModel, ConfigDict

from scenefoundry.domain.screenplay import (
    Screenplay,
    ScreenplayFormat,
    ScreenplayVersion,
    screenplay_version_id,
)


class PreparedScreenplayVersion(BaseModel):
    """A new version or an immutable version matched by a retry."""

    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
    )

    version: ScreenplayVersion
    existing: bool


def _matches_request(
    version: ScreenplayVersion,
    *,
    parent_version_id: str | None,
    screenplay: Screenplay,
    change_note: str | None,
) -> bool:
    return (
        version.parent_version_id == parent_version_id
        and version.screenplay == screenplay
        and version.change_note == change_note
    )


def prepare_screenplay_version(
    *,
    screenplay_id: str,
    existing_versions: tuple[ScreenplayVersion, ...],
    parent_version_id: str | None,
    title: str,
    format: ScreenplayFormat,
    content: str,
    change_note: str | None,
) -> PreparedScreenplayVersion:
    """Derive version lineage without trusting browser metadata."""

    screenplay = Screenplay(
        title=title,
        format=format,
        content=content,
    )

    if not existing_versions:
        if parent_version_id is not None:
            raise ValueError(
                "Initial screenplay import cannot specify a parent."
            )

        note = change_note or "Imported in the Develop workspace."
        version = ScreenplayVersion(
            screenplay_id=screenplay_id,
            version_id=screenplay_version_id(screenplay_id, 1),
            version=1,
            parent_version_id=None,
            source="imported",
            screenplay=screenplay,
            content_sha256=screenplay.sha256,
            created_by="director_workspace",
            change_note=note,
        )
        return PreparedScreenplayVersion(
            version=version,
            existing=False,
        )

    ordered = tuple(
        sorted(
            existing_versions,
            key=lambda item: item.version,
        )
    )
    if any(
        item.screenplay_id != screenplay_id
        for item in ordered
    ):
        raise ValueError("Screenplay history contains another identity.")

    if parent_version_id is None:
        initial = ordered[0]
        initial_note = change_note or "Imported in the Develop workspace."
        if _matches_request(
            initial,
            parent_version_id=None,
            screenplay=screenplay,
            change_note=initial_note,
        ):
            return PreparedScreenplayVersion(
                version=initial,
                existing=True,
            )
        raise ValueError("Screenplay has already been initialized.")

    parent = next(
        (
            item
            for item in ordered
            if item.version_id == parent_version_id
        ),
        None,
    )
    if parent is None:
        raise ValueError("Parent screenplay version does not exist.")
    if not change_note:
        raise ValueError("Screenplay edits require a change note.")

    child_number = parent.version + 1
    existing_child = next(
        (
            item
            for item in ordered
            if item.version == child_number
        ),
        None,
    )
    if existing_child is not None:
        if _matches_request(
            existing_child,
            parent_version_id=parent_version_id,
            screenplay=screenplay,
            change_note=change_note,
        ):
            return PreparedScreenplayVersion(
                version=existing_child,
                existing=True,
            )
        raise ValueError(
            "Parent screenplay version already has a different child."
        )

    if parent.version_id != ordered[-1].version_id:
        raise ValueError(
            "Screenplay edit must use the latest version as its parent."
        )

    version = ScreenplayVersion(
        screenplay_id=screenplay_id,
        version_id=screenplay_version_id(
            screenplay_id,
            child_number,
        ),
        version=child_number,
        parent_version_id=parent.version_id,
        source="edited",
        screenplay=screenplay,
        content_sha256=screenplay.sha256,
        created_by="director_workspace",
        change_note=change_note,
    )
    return PreparedScreenplayVersion(
        version=version,
        existing=False,
    )
