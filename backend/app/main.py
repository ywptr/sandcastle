from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.stories import router as stories_router
from app.api.story_import import router as story_import_router
from app.api.world import router as world_router
from app.api.media import router as media_router
from app.api.media_executions import router as media_execution_router
from app.api.artifacts import router as artifact_router
from app.api.canon_intelligence import router as canon_intelligence_router
from app.api.canon_library import router as canon_library_router
from app.api.universes import router as universe_router
from app.api.guidance import router as guidance_router
from app.api.media_adaptation import router as media_adaptation_router
from app.api.workflows import router as workflow_router

app = FastAPI(
    title="Sandcastle",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5182",
        "http://127.0.0.1:5182",
        "http://192.168.0.99:5182",
        "https://sandcastle-gui.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    auth_router,
    prefix="/api",
)

app.include_router(story_import_router, prefix="/api")

app.include_router(
    stories_router,
    prefix="/api",
)

app.include_router(world_router, prefix="/api")
app.include_router(media_router, prefix="/api")
app.include_router(media_execution_router, prefix="/api")
app.include_router(artifact_router, prefix="/api")
app.include_router(canon_intelligence_router, prefix="/api")
app.include_router(canon_library_router, prefix="/api")
app.include_router(universe_router, prefix="/api")
app.include_router(guidance_router, prefix="/api")
app.include_router(media_adaptation_router, prefix="/api")
app.include_router(workflow_router, prefix="/api")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "sandcastle",
    }

from app.api.llm_settings import router as llm_settings_router
app.include_router(llm_settings_router, prefix="/api")

from app.api.production import router as production_router
app.include_router(production_router, prefix="/api")

from app.api.creative_direction import router as creative_direction_router
app.include_router(creative_direction_router, prefix="/api")

from app.api.languages import router as language_router
app.include_router(language_router, prefix="/api")
