from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.stories import router as stories_router
from app.api.world import router as world_router
from app.api.media import router as media_router
from app.api.media_executions import router as media_execution_router
from app.api.artifacts import router as artifact_router
from app.api.canon_intelligence import router as canon_intelligence_router
from app.api.canon_library import router as canon_library_router
from app.api.universes import router as universe_router
from app.api.guidance import router as guidance_router
from app.api.media_adaptation import router as media_adaptation_router

app = FastAPI(
    title="Sandcastle",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://192.168.0.99:5173",
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


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "sandcastle",
    }
