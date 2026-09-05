from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from scenefoundry.agents.director import build_director


async def run_director(
    brief: str,
    model: str,
) -> tuple[str, list[dict[str, object]]]:
    """Return final response text and unaggregated provider usage records."""
    brief = brief.strip()
    if not brief or len(brief) > 4000:
        raise ValueError("Brief must contain between 1 and 4000 characters.")

    sessions = InMemorySessionService()
    session = await sessions.create_session(
        app_name="scenefoundry",
        user_id="local",
    )
    message = types.Content(
        role="user",
        parts=[types.Part(text=brief)],
    )
    usage: list[dict[str, object]] = []
    final_text = ""

    async with Runner(
        app_name="scenefoundry",
        agent=build_director(model),
        session_service=sessions,
    ) as runner:
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=message,
            run_config=RunConfig(
                max_llm_calls=1,
                streaming_mode=StreamingMode.NONE,
            ),
        ):
            if event.usage_metadata is not None:
                usage.append(
                    event.usage_metadata.model_dump(mode="json", exclude_none=True)
                )
            if event.error_code:
                raise RuntimeError(
                    f"Director failed: {event.error_code}: {event.error_message}"
                )
            if event.is_final_response() and event.content:
                final_text = "".join(
                    part.text
                    for part in event.content.parts or []
                    if part.text and not part.thought
                )

    return final_text, usage