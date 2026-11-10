"""Semantic analyzer protocol; request-scoped provider composition is outside the domain."""
from typing import Protocol
from fastapi import Depends
from sqlalchemy.orm import Session
from app.api.dependencies import get_db, get_current_identity
from app.auth.identity import AuthenticatedIdentity
from app.llm.resolver import resolve_adapter
from app.story_import.schemas import ImportAnalysis, ImportAnalysisRequest


class StoryImportAnalyzer(Protocol):
    async def analyze(self, request: ImportAnalysisRequest) -> ImportAnalysis: ...


def get_import_analyzer(db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)) -> StoryImportAnalyzer:
    return resolve_adapter(db, identity.user_id, "story_importer")
