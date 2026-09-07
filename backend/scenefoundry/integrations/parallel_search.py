"""Parallel Search runtime adapter for production research."""

import os
from typing import Protocol

from parallel import Parallel

from scenefoundry.domain.research import (
    ProductionResearch,
    ProductionResearchRequest,
    ResearchSource,
)


class ParallelSearchClient(Protocol):
    """Small interface that keeps the provider adapter testable."""

    def search(self, **kwargs) -> object:
        ...


def build_parallel_client(
    api_key: str | None = None,
) -> Parallel:
    """Create the official Parallel client from a protected key."""

    resolved_key = (
        api_key
        if api_key is not None
        else os.environ.get("PARALLEL_API_KEY", "")
    ).strip()

    if not resolved_key:
        raise RuntimeError(
            "PARALLEL_API_KEY is required for live research."
        )

    return Parallel(api_key=resolved_key)


def _attribute(
    value: object,
    name: str,
    default=None,
):
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def search_production_references(
    client: ParallelSearchClient,
    request: ProductionResearchRequest,
) -> ProductionResearch:
    """Execute one bounded, citation-preserving Parallel search."""

    response = client.search(
        objective=request.objective,
        search_queries=list(request.search_queries),
        mode="fast",
        max_chars_total=min(
            12_000,
            request.max_results * 2_000,
        ),
    )

    search_id = str(
        _attribute(response, "search_id", "")
    ).strip()
    if not search_id:
        raise RuntimeError(
            "Parallel returned no search identifier."
        )

    sources: list[ResearchSource] = []
    raw_results = list(
        _attribute(response, "results", ()) or ()
    )
    for result in raw_results[: request.max_results]:
        url = str(_attribute(result, "url", "")).strip()
        title = str(_attribute(result, "title", "")).strip()
        raw_excerpts = (
            _attribute(result, "excerpts", ()) or ()
        )
        excerpts = tuple(
            str(excerpt).strip()
            for excerpt in raw_excerpts
            if str(excerpt).strip()
        )

        if not url or not excerpts:
            continue

        sources.append(
            ResearchSource(
                url=url,
                title=title or url,
                excerpts=excerpts[:8],
            )
        )

    if not sources:
        raise RuntimeError(
            "Parallel returned no citation-ready sources."
        )

    warnings = tuple(
        str(warning).strip()
        for warning in (
            _attribute(response, "warnings", ()) or ()
        )
        if str(warning).strip()
    )

    return ProductionResearch(
        search_id=search_id,
        objective=request.objective,
        search_queries=request.search_queries,
        sources=tuple(sources),
        warnings=warnings,
    )
