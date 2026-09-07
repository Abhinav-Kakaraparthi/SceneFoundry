"""Authenticated Parallel production-research API."""

from typing import Annotated

from fastapi import (
    APIRouter,
    HTTPException,
    Path,
    Response,
    status,
)
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
)

from scenefoundry.api.auth import CurrentUser
from scenefoundry.api.projects import Database, ResourceId
from scenefoundry.domain.research import ProductionResearchRequest
from scenefoundry.domain.research_record import (
    ProductionResearchRecord,
    create_production_research_record,
    production_research_id,
)
from scenefoundry.integrations.parallel_search import (
    build_parallel_client,
    search_production_references,
)
from scenefoundry.storage.research import (
    find_production_research,
    list_production_research,
    read_production_research,
    save_production_research,
)
from scenefoundry.storage.users import read_verified_user


router = APIRouter(
    prefix="/v1/projects/{project_id}/research",
    tags=["production-research"],
)
ResearchId = Annotated[
    str,
    Path(pattern=r"^research_[a-f0-9]{24}$"),
]


class ProductionResearchPayload(BaseModel):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    objective: str = Field(min_length=1, max_length=1000)
    search_queries: list[str] = Field(
        min_length=2,
        max_length=3,
    )
    max_results: int = Field(default=5, ge=1, le=10)

    def to_request(self) -> ProductionResearchRequest:
        return ProductionResearchRequest(
            objective=self.objective,
            search_queries=tuple(self.search_queries),
            max_results=self.max_results,
        )


class ProductionResearchResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    created: bool
    record: ProductionResearchRecord


def _require_registered_identity(
    db,
    current_user,
):
    try:
        stored = read_verified_user(
            db,
            uid=current_user.uid,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verified user registration is required.",
        ) from error

    if (
        stored.uid != current_user.uid
        or stored.email != current_user.email
        or stored.provider != current_user.provider
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Stored user identity is inconsistent.",
        )

    return stored


@router.post(
    "",
    response_model=ProductionResearchResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_research(
    project_id: ResourceId,
    payload: ProductionResearchPayload,
    response: Response,
    current_user: CurrentUser,
    db: Database,
) -> ProductionResearchResponse:
    """Run or reuse one bounded, authenticated Parallel search."""

    registered = _require_registered_identity(db, current_user)

    try:
        request = payload.to_request()
    except (TypeError, ValueError, ValidationError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Production research request is invalid.",
        ) from error

    research_id = production_research_id(
        studio_project_id=project_id,
        requested_by=registered.uid,
        request=request,
    )
    existing = find_production_research(
        db,
        studio_project_id=project_id,
        research_id=research_id,
    )

    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return ProductionResearchResponse(
            created=False,
            record=existing,
        )

    try:
        parallel = build_parallel_client()
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Parallel production research is not configured.",
        ) from error

    try:
        evidence = search_production_references(
            parallel,
            request,
        )
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Parallel production research failed.",
        ) from error

    record = create_production_research_record(
        studio_project_id=project_id,
        requested_by=registered.uid,
        request=request,
        evidence=evidence,
    )

    try:
        created = save_production_research(
            db,
            record=record,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    if not created:
        response.status_code = status.HTTP_200_OK

    return ProductionResearchResponse(
        created=created,
        record=record,
    )


@router.get(
    "",
    response_model=list[ProductionResearchRecord],
)
def list_research(
    project_id: ResourceId,
    current_user: CurrentUser,
    db: Database,
) -> list[ProductionResearchRecord]:
    registered = _require_registered_identity(db, current_user)
    return list(
        list_production_research(
            db,
            studio_project_id=project_id,
            requested_by=registered.uid,
        )
    )


@router.get(
    "/{research_id}",
    response_model=ProductionResearchRecord,
)
def read_research(
    project_id: ResourceId,
    research_id: ResearchId,
    current_user: CurrentUser,
    db: Database,
) -> ProductionResearchRecord:
    registered = _require_registered_identity(db, current_user)

    try:
        record = read_production_research(
            db,
            studio_project_id=project_id,
            research_id=research_id,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    if record.requested_by != registered.uid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Production research does not exist.",
        )

    return record
