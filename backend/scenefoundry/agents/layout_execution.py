"""Execute layout generation; validate output after durable accounting."""

import json

from scenefoundry.agents.layout import build_layout_agent
from scenefoundry.agents.runtime import run_agent
from scenefoundry.domain.layout import ShotLayout
from scenefoundry.domain.shot import ShotSpec


async def run_layout(
    shot: ShotSpec,
    model: str,
) -> tuple[str, list[dict[str, object]]]:
    """Return raw response and usage without discarding invalid output."""
    prompt = json.dumps(
        {"shot": shot.model_dump(mode="json")},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return await run_agent(build_layout_agent(model), prompt)


def validate_layout(text: str, *, expected_shot_id: str) -> ShotLayout:
    """Validate geometry and bind the result to its requested shot."""
    layout = ShotLayout.model_validate_json(text)
    if layout.shot_id != expected_shot_id:
        raise ValueError(
            f"Expected layout for {expected_shot_id}; received {layout.shot_id}."
        )
    return layout
