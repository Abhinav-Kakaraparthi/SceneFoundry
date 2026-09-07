import os
from pathlib import Path

from scenefoundry.api.cloud_videos import router as cloud_videos_router
from scenefoundry.api.previews import router as previews_router
from scenefoundry.api.generation import router as generation_router
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from scenefoundry.api.video_completion import router as video_completion_router

from scenefoundry.api.shot_videos import router as shot_videos_router

from scenefoundry.api.veo import router as veo_router

from scenefoundry.api.scenes import router as scenes_router
from scenefoundry.api.projects import router as projects_router
from scenefoundry.api.project_catalog import router as project_catalog_router
from scenefoundry.api.auth import router as auth_router
from scenefoundry.api.approvals import router as approvals_router
from scenefoundry.api.artifacts import router as artifacts_router
from scenefoundry.api.revision_status import router as revision_status_router
from scenefoundry.api.revision_edits import router as revision_edits_router
from scenefoundry.api.revisions import router as revisions_router
from scenefoundry.api.screenplays import router as screenplays_router
from scenefoundry.api.research import router as research_router

app = FastAPI(title="SceneFoundry", version="0.1.0")
app.include_router(scenes_router)
app.include_router(auth_router)
app.include_router(approvals_router)
app.include_router(project_catalog_router)
app.include_router(projects_router)
app.include_router(artifacts_router)
app.include_router(revision_status_router)
app.include_router(revision_edits_router)
app.include_router(revisions_router)
app.include_router(screenplays_router)
app.include_router(research_router)
app.include_router(previews_router)
app.include_router(generation_router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}

app.include_router(veo_router)
app.include_router(cloud_videos_router)

app.include_router(shot_videos_router)

app.include_router(video_completion_router)

web_directory = os.environ.get("SCENEFOUNDRY_WEB_DIR")
if web_directory:
    resolved_web_directory = Path(web_directory)
    if not resolved_web_directory.is_dir():
        raise RuntimeError("Configured frontend directory does not exist.")
    app.mount(
        "/",
        StaticFiles(directory=resolved_web_directory, html=True),
        name="frontend",
    )
