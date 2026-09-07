from scenefoundry.agents.director import build_director
from scenefoundry.agents.runtime import run_agent
from scenefoundry.domain.director_grounding import (
    DirectorGrounding,
    render_grounded_director_brief,
)
from scenefoundry.domain.production_direction import (
    ProductionDirection,
    render_production_director_brief,
)


async def run_director(
    brief: str,
    model: str,
    *,
    grounding: DirectorGrounding | None = None,
    direction: ProductionDirection | None = None,
) -> tuple[str, list[dict[str, object]]]:
    """Execute the director with optional server-verified research."""

    brief = brief.strip()
    if not brief or len(brief) > 4000:
        raise ValueError(
            "Brief must contain between 1 and 4000 characters."
        )

    director_input = (
        brief
        if direction is None
        else render_production_director_brief(
            brief,
            direction,
        )
    )
    if grounding is not None:
        director_input = render_grounded_director_brief(
            director_input,
            grounding,
        )

    return await run_agent(
        build_director(model),
        director_input,
    )
