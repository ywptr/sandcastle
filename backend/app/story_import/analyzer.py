"""Provider boundary and optional composition. Never receives identity or a DB session."""
import os
from typing import Protocol

from fastapi import HTTPException

from app.story_import.schemas import ImportAnalysis, ImportAnalysisRequest


class StoryImportAnalyzer(Protocol):
    async def analyze(self, request: ImportAnalysisRequest) -> ImportAnalysis: ...


def get_import_analyzer() -> StoryImportAnalyzer:
    if not os.getenv("OPENAI_API_KEY") or not os.getenv("SANDCASTLE_TEXT_MODEL"):
        raise HTTPException(503, "Story import analysis is not configured")
    try:
        from app.story_import.openai_analyzer import OpenAIStoryImportAnalyzer
    except ImportError as error:
        raise HTTPException(503, "Story import analysis provider is unavailable") from error
    return OpenAIStoryImportAnalyzer()
