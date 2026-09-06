from scenefoundry.api.previews import router as previews_router
from scenefoundry.api.generation import router as generation_router
from fastapi import FastAPI

from scenefoundry.api.video_completion import router as video_completion_router

from scenefoundry.api.shot_videos import router as shot_videos_router

from scenefoundry.api.veo import router as veo_router

from scenefoundry.api.scenes import router as scenes_router
from scenefoundry.api.projects import router as projects_router

app = FastAPI(title="SceneFoundry", version="0.1.0")
app.include_router(scenes_router)
app.include_router(projects_router)
app.include_router(previews_router)
app.include_router(generation_router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}

app.include_router(veo_router)

app.include_router(shot_videos_router)

app.include_router(video_completion_router)
