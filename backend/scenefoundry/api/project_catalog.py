"""Authenticated production creation and discovery API."""

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field

from scenefoundry.api.auth import RegisteredUser
from scenefoundry.api.projects import Database, ResourceId
from scenefoundry.domain.project import (
    AspectRatio,
    ProductionProject,
    ProjectGenre,
    VisualStyle,
    build_production_project,
)
from scenefoundry.storage.projects import (
    list_production_projects,
    read_production_project,
    save_production_project,
)


router = APIRouter(prefix="/v1/projects", tags=["production-catalog"])


class CreateProductionPayload(BaseModel):
    """User-selectable production configuration."""

    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    creation_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    title: str = Field(min_length=1, max_length=120)
    premise: str = Field(min_length=1, max_length=4000)
    genre: ProjectGenre
    visual_style: VisualStyle
    aspect_ratio: AspectRatio
    episode_count: int = Field(ge=1, le=12)
    seconds_per_episode: int = Field(ge=4, le=120)
    budget_cents: int = Field(ge=0, le=100_000)

    def build(self, *, created_by: str) -> ProductionProject:
        return build_production_project(
            creation_id=self.creation_id,
            created_by=created_by,
            title=self.title,
            premise=self.premise,
            genre=self.genre,
            visual_style=self.visual_style,
            aspect_ratio=self.aspect_ratio,
            episode_count=self.episode_count,
            seconds_per_episode=self.seconds_per_episode,
            budget_cents=self.budget_cents,
        )


class CreateProductionResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    created: bool
    project: ProductionProject


@router.post(
    "",
    response_model=CreateProductionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_production(
    payload: CreateProductionPayload,
    response: Response,
    user: RegisteredUser,
    db: Database,
) -> CreateProductionResponse:
    """Create a production owned by the authenticated user."""

    project = payload.build(created_by=user.uid)

    try:
        created, stored = save_production_project(
            db,
            project=project,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    if not created:
        response.status_code = status.HTTP_200_OK

    return CreateProductionResponse(
        created=created,
        project=stored,
    )


@router.get(
    "",
    response_model=list[ProductionProject],
)
def list_productions(
    user: RegisteredUser,
    db: Database,
) -> list[ProductionProject]:
    """List only productions belonging to the authenticated user."""

    return list(
        list_production_projects(
            db,
            created_by=user.uid,
        )
    )


@router.get(
    "/{project_id}",
    response_model=ProductionProject,
)
def read_production(
    project_id: ResourceId,
    user: RegisteredUser,
    db: Database,
) -> ProductionProject:
    """Read one production without disclosing another user's data."""

    try:
        return read_production_project(
            db,
            project_id=project_id,
            created_by=user.uid,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Production project does not exist.",
        ) from error
