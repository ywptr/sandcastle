from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.stories import router as stories_router

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
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    stories_router,
    prefix="/api",
)

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "sandcastle",
    }