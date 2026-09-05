from fastapi import FastAPI

from scenefoundry.api.scenes import router as scenes_router

app = FastAPI(title="SceneFoundry", version="0.1.0")
app.include_router(scenes_router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}