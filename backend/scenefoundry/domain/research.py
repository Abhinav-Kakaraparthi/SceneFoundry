"""Typed production-research evidence returned by Parallel Search."""

from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class ProductionResearchRequest(BaseModel):
    """Bounded live-web research requested by a production agent."""

    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
    )

    objective: str = Field(min_length=1, max_length=1000)
    search_queries: tuple[str, ...] = Field(
        min_length=2,
        max_length=3,
    )
    max_results: int = Field(default=5, ge=1, le=10)

    @field_validator("objective", mode="before")
    @classmethod
    def normalize_objective(cls, value):
        if not isinstance(value, str):
            raise TypeError("Research objective must be text.")
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Research objective cannot be blank.")
        return normalized

    @field_validator("search_queries", mode="before")
    @classmethod
    def normalize_queries(cls, value):
        if not isinstance(value, (list, tuple)):
            raise TypeError("Search queries must be a sequence.")

        queries: list[str] = []
        for query in value:
            if not isinstance(query, str):
                raise TypeError("Each search query must be text.")
            normalized = " ".join(query.split())
            if not normalized:
                raise ValueError("Search queries cannot be blank.")
            if len(normalized) > 200:
                raise ValueError(
                    "Search queries cannot exceed 200 characters."
                )
            queries.append(normalized)

        return tuple(queries)

    @model_validator(mode="after")
    def require_distinct_queries(self) -> Self:
        normalized = {
            query.casefold()
            for query in self.search_queries
        }
        if len(normalized) != len(self.search_queries):
            raise ValueError("Search queries must be distinct.")
        return self


class ResearchSource(BaseModel):
    """One citation-ready source returned by Parallel."""

    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
    )

    url: str = Field(
        min_length=8,
        max_length=2048,
        pattern=r"^https?://",
    )
    title: str = Field(min_length=1, max_length=500)
    excerpts: tuple[str, ...] = Field(min_length=1, max_length=8)

    @field_validator("excerpts", mode="before")
    @classmethod
    def normalize_excerpts(cls, value):
        if not isinstance(value, (list, tuple)):
            raise TypeError("Source excerpts must be a sequence.")

        excerpts = tuple(
            excerpt.strip()
            for excerpt in value
            if isinstance(excerpt, str) and excerpt.strip()
        )
        if not excerpts:
            raise ValueError(
                "A research source requires usable excerpts."
            )
        return excerpts


class ProductionResearch(BaseModel):
    """Immutable evidence from one Parallel Search execution."""

    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
    )

    provider: Literal["parallel"] = "parallel"
    mode: Literal["fast"] = "fast"
    search_id: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=1, max_length=1000)
    search_queries: tuple[str, ...] = Field(
        min_length=2,
        max_length=3,
    )
    sources: tuple[ResearchSource, ...] = Field(
        min_length=1,
        max_length=10,
    )
    warnings: tuple[str, ...] = ()
