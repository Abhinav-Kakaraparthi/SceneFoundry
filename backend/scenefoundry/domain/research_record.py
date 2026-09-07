"""Immutable provenance for Parallel production research."""

import hashlib
import json
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from scenefoundry.domain.research import (
    ProductionResearch,
    ProductionResearchRequest,
)


def research_request_sha256(
    request: ProductionResearchRequest,
) -> str:
    canonical = json.dumps(
        request.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def production_research_id(
    *,
    studio_project_id: str,
    requested_by: str,
    request: ProductionResearchRequest,
) -> str:
    identity = {
        "studio_project_id": studio_project_id,
        "requested_by": requested_by,
        "request_sha256": research_request_sha256(request),
    }
    canonical = json.dumps(
        identity,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"research_{digest[:24]}"


class ProductionResearchRecord(BaseModel):
    """One immutable, user-attributed partner research result."""

    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
    )

    research_id: str = Field(
        pattern=r"^research_[a-f0-9]{24}$",
    )
    studio_project_id: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    requested_by: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    request_sha256: str = Field(
        pattern=r"^[a-f0-9]{64}$",
    )
    max_results: int = Field(ge=1, le=10)
    evidence: ProductionResearch

    @model_validator(mode="after")
    def validate_identity(self) -> Self:
        request = ProductionResearchRequest(
            objective=self.evidence.objective,
            search_queries=self.evidence.search_queries,
            max_results=self.max_results,
        )
        expected_hash = research_request_sha256(request)
        expected_id = production_research_id(
            studio_project_id=self.studio_project_id,
            requested_by=self.requested_by,
            request=request,
        )

        if self.request_sha256 != expected_hash:
            raise ValueError(
                "Research request fingerprint is inconsistent."
            )
        if self.research_id != expected_id:
            raise ValueError(
                "Research record identity is inconsistent."
            )

        return self


def create_production_research_record(
    *,
    studio_project_id: str,
    requested_by: str,
    request: ProductionResearchRequest,
    evidence: ProductionResearch,
) -> ProductionResearchRecord:
    if evidence.objective != request.objective:
        raise ValueError(
            "Research evidence objective differs from the request."
        )
    if evidence.search_queries != request.search_queries:
        raise ValueError(
            "Research evidence queries differ from the request."
        )

    return ProductionResearchRecord(
        research_id=production_research_id(
            studio_project_id=studio_project_id,
            requested_by=requested_by,
            request=request,
        ),
        studio_project_id=studio_project_id,
        requested_by=requested_by,
        request_sha256=research_request_sha256(request),
        max_results=request.max_results,
        evidence=evidence,
    )
