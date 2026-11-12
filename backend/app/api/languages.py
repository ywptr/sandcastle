from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from app.api.dependencies import get_current_identity
from app.languages.service import DetectionRequest, detect

router = APIRouter(tags=["languages"])


@router.post("/languages/detect")
def detect_language(request: DetectionRequest, identity=Depends(get_current_identity)):
    return JSONResponse(detect(request.text), headers={"Cache-Control": "no-store"})
