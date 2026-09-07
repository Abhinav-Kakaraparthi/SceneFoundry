"""Import, edit, and read immutable screenplay versions."""

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field

from scenefoundry.api.projects import Database, ResourceId
from scenefoundry.domain.screenplay import (
    ScreenplayFormat,
    ScreenplayVersion,
)
from scenefoundry.domain.screenplay_workflow import (
    prepare_screenplay_version,
)
from scenefoundry.storage.screenplays import (
    list_screenplay_versions,
    read_screenplay_version,
    save_screenplay_version,
)

router = APIRouter(
    prefix="/v1/projects/{project_id}/screenplays",
    tags=["screenplays"],
)


class CreateScreenplayVersionRequest(BaseModel):
    """Creative text accepted from the Develop workspace."""

    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    parent_version_id: str | None = Field(
        default=None,
        pattern=r"^[a-z][a-z0-9_]{0,63}$",
    )
    title: str = Field(min_length=1, max_length=200)
    format: ScreenplayFormat
    content: str = Field(min_length=1, max_length=500_000)
    change_note: str | None = Field(default=None, max_length=2000)


class CreateScreenplayVersionResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    created: bool
    version: ScreenplayVersion


@router.post(
    "/{screenplay_id}/versions",
    response_model=CreateScreenplayVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_screenplay_version(
    project_id: ResourceId,
    screenplay_id: ResourceId,
    request: CreateScreenplayVersionRequest,
    response: Response,
    db: Database,
) -> CreateScreenplayVersionResponse:
    try:
        existing = list_screenplay_versions(
            db,
            studio_project_id=project_id,
            screenplay_id=screenplay_id,
        )
        prepared = prepare_screenplay_version(
            screenplay_id=screenplay_id,
            existing_versions=existing,
            parent_version_id=request.parent_version_id,
            title=request.title,
            format=request.format,
            content=request.content,
            change_note=request.change_note,
        )
        created = save_screenplay_version(
            db,
            studio_project_id=project_id,
            version=prepared.version,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    if not created:
        response.status_code = status.HTTP_200_OK

    return CreateScreenplayVersionResponse(
        created=created,
        version=prepared.version,
    )


@router.get(
    "/{screenplay_id}/versions",
    response_model=tuple[ScreenplayVersion, ...],
)
def list_versions(
    project_id: ResourceId,
    screenplay_id: ResourceId,
    db: Database,
) -> tuple[ScreenplayVersion, ...]:
    return list_screenplay_versions(
        db,
        studio_project_id=project_id,
        screenplay_id=screenplay_id,
    )


@router.get(
    "/{screenplay_id}/versions/{version_id}",
    response_model=ScreenplayVersion,
)
def read_version(
    project_id: ResourceId,
    screenplay_id: ResourceId,
    version_id: ResourceId,
    db: Database,
) -> ScreenplayVersion:
    try:
        return read_screenplay_version(
            db,
            studio_project_id=project_id,
            screenplay_id=screenplay_id,
            version_id=version_id,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
