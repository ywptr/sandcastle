from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.api.dependencies import get_current_identity
from app.auth.identity import AuthenticatedIdentity
from app.story_import.analyzer import StoryImportAnalyzer, get_import_analyzer
from app.story_import.schemas import ImportAnalysisRequest, ImportProposal
from app.story_import.service import InvalidImportAnalysis, analyze_import

router = APIRouter(prefix="/stories/import", tags=["story-import"])


@router.post("/analyze", response_model=ImportProposal)
async def analyze_story_import(
    request: ImportAnalysisRequest,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    analyzer: StoryImportAnalyzer = Depends(get_import_analyzer),
):
    try:
        proposal = await analyze_import(request, analyzer)
    except InvalidImportAnalysis as error:
        raise HTTPException(502, "Import analysis failed or returned an invalid proposal") from error
    return JSONResponse(content=proposal.model_dump(mode="json"), headers={"Cache-Control": "no-store"})
