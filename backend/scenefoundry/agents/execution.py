from scenefoundry.agents.director import build_director
from scenefoundry.agents.runtime import run_agent


async def run_director(
    brief: str,
    model: str,
) -> tuple[str, list[dict[str, object]]]:
    """Validate the brief and execute the director through the shared runner."""
    brief = brief.strip()
    if not brief or len(brief) > 4000:
        raise ValueError("Brief must contain between 1 and 4000 characters.")

    return await run_agent(build_director(model), brief)
