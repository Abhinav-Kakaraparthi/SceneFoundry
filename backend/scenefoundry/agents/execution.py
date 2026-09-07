from scenefoundry.agents.director import build_director
from scenefoundry.agents.runtime import run_agent
from scenefoundry.domain.director_grounding import (
    DirectorGrounding,
    render_grounded_director_brief,
)


async def run_director(
    brief: str,
    model: str,
    *,
    grounding: DirectorGrounding | None = None,
) -> tuple[str, list[dict[str, object]]]:
    """Execute the director with optional server-verified research."""

    brief = brief.strip()
    if not brief or len(brief) > 4000:
        raise ValueError(
            "Brief must contain between 1 and 4000 characters."
        )

    director_input = (
        brief
        if grounding is None
        else render_grounded_director_brief(
            brief,
            grounding,
        )
    )

    return await run_agent(
        build_director(model),
        director_input,
    )
