from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_identity, get_db
from app.creative_direction import service
from app.creative_direction.registry import styles, style_snapshot
from app.creative_direction.schemas import DirectionInput, RecommendationInput, Recommendation, StartStory
from app.llm.resolver import resolve_adapter
from app.stories.schemas import StoryResponse

router = APIRouter(tags=["creative-direction"])


def get_recommender(db: Session = Depends(get_db), identity=Depends(get_current_identity)):
    return resolve_adapter(db, identity.user_id, "creative_writer", capability="creative_direction")


@router.get("/styles")
def list_styles(identity=Depends(get_current_identity)):
    return styles()


@router.post("/styles/recommend", response_model=Recommendation)
async def recommend(request: RecommendationInput, identity=Depends(get_current_identity), recommender=Depends(get_recommender)):
    try:
        proposal = Recommendation.model_validate(await recommender.recommend({"narrative_data":request.model_dump(),"style_registry":styles()}))
        style_snapshot(proposal.storytelling_style_id)
        if proposal.target_format != request.target_format or (request.language and proposal.language != request.language):
            raise ValueError()
        return JSONResponse(proposal.model_dump(mode="json"),headers={"Cache-Control":"no-store"})
    except Exception:
        raise HTTPException(502,"Creative recommendation unavailable. Continue manually.") from None


@router.post("/stories/start",response_model=StoryResponse)
def start_story(request: StartStory,db: Session=Depends(get_db),identity=Depends(get_current_identity)):
    return service.start(db,identity.user_id,request)


@router.get("/stories/{story_id}/creative-direction")
def read_direction(story_id: str,db: Session=Depends(get_db),identity=Depends(get_current_identity)):
    row = service.latest(db,identity.user_id,story_id)
    return JSONResponse(service.view(row) if row else None,headers={"Cache-Control":"no-store"})


@router.put("/stories/{story_id}/creative-direction")
def save_direction(story_id: str,request: DirectionInput,db: Session=Depends(get_db),identity=Depends(get_current_identity)):
    story = service.require_story(db,identity.user_id,story_id)
    row = service.append(db,identity.user_id,story,request)
    service.commit(db)
    db.refresh(row)
    return service.view(row)
