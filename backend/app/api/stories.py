from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_current_identity,
    get_db,
)
from app.auth.identity import AuthenticatedIdentity
from app.authority.adapters.local import LocalAuthorityEvaluator
from app.canon.schemas import (
    CanonEntryCreate,
    CanonEntryResponse,
)
from app.canon.service import (
    create_canon_entry,
    list_canon_entries,
)
from app.db.models.story import Story
from app.stories.action_queries import (
    get_latest_decision,
    list_story_actions,
)
from app.stories.action_schemas import (
    StoryActionCreate,
    StoryActionListItem,
    StoryActionResponse,
)
from app.stories.action_service import (
    create_story_action,
    evaluate_story_action,
)
from app.stories.schemas import (
    StoryCreate,
    StoryResponse,
)
from app.stories.service import (
    create_story,
    get_story,
    list_stories,
)

from app.stories.adapters.openai_generator import (
    OpenAIStoryGenerator,
)
from app.stories.scene_schemas import (
    SceneGenerateRequest,
    SceneGenerateResponse,
    SceneResponse,
)
from app.stories.scene_service import (
    generate_scene,
    list_scenes,
)

router = APIRouter(
    prefix="/stories",
    tags=["stories"],
)

authority_evaluator = LocalAuthorityEvaluator()

story_generator = OpenAIStoryGenerator()

def require_story(
    db: Session,
    story_id: str,
    identity: AuthenticatedIdentity,
) -> Story:
    story = get_story(
        db,
        story_id,
        identity.user_id,
    )

    if story is None:
        raise HTTPException(
            status_code=404,
            detail="Story not found",
        )

    return story

def action_to_list_item(
    db: Session,
    action,
) -> StoryActionListItem:
    decision = get_latest_decision(
        db,
        action.action_id,
    )
    return StoryActionListItem(
        action_id=action.action_id,
        story_id=action.story_id,
        action_type=action.action_type,
        request=action.request,
        status=action.status,
        created_at=action.created_at,
        decision=decision,
    )

def action_to_response(
    action,
    decision,
) -> StoryActionResponse:
    return StoryActionResponse(
        action_id=action.action_id,
        story_id=action.story_id,
        action_type=action.action_type,
        request=action.request,
        status=action.status,
        created_at=action.created_at,
        decision=decision,
    )

@router.post(
    "",
    response_model=StoryResponse,
    status_code=201,
)
def create_story_endpoint(
    payload: StoryCreate,
    db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(
        get_current_identity
    ),
):
    return create_story(
        db,
        identity.user_id,
        payload.title,
        payload.premise,
        payload.objective,
    )


@router.get(
    "",
    response_model=list[StoryResponse],
)
def list_stories_endpoint(
    db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(
        get_current_identity
    ),
):
    return list_stories(
        db,
        identity.user_id,
    )


@router.get(
    "/{story_id}",
    response_model=StoryResponse,
)
def get_story_endpoint(
    story_id: str,
    db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(
        get_current_identity
    ),
):
    return require_story(
        db,
        story_id,
        identity,
    )


@router.post(
    "/{story_id}/canon",
    response_model=CanonEntryResponse,
    status_code=201,
)
def create_canon_entry_endpoint(
    story_id: str,
    request: CanonEntryCreate,
    db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(
        get_current_identity
    ),
):
    require_story(
        db,
        story_id,
        identity,
    )

    return create_canon_entry(
        db,
        story_id=story_id,
        entry_type=request.type,
        key=request.key,
        value=request.value,
    )


@router.get(
    "/{story_id}/canon",
    response_model=list[CanonEntryResponse],
)
def list_canon_entries_endpoint(
    story_id: str,
    db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(
        get_current_identity
    ),
):
    require_story(
        db,
        story_id,
        identity,
    )

    return list_canon_entries(
        db,
        story_id,
    )

@router.post(
    "/{story_id}/actions",
    response_model=StoryActionResponse,
    status_code=201,
)
def create_story_action_endpoint(
    story_id: str,
    request: StoryActionCreate,
    db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(
        get_current_identity
    ),
):
    story = require_story(
        db,
        story_id,
        identity,
    )

    action = create_story_action(
        db,
        story=story,
        action_type=request.action_type,
        request=request.request,
    )

    decision = evaluate_story_action(
        db,
        story=story,
        action=action,
        evaluator=authority_evaluator,
    )

    return action_to_response(
        action,
        decision,
    )

@router.get(
    "/{story_id}/actions",
    response_model=list[StoryActionListItem],
)
def list_story_actions_endpoint(
    story_id: str,
    db: Session = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(
        get_current_identity
    ),
):
    require_story(
        db,
        story_id,
        identity,
    )

    actions = list_story_actions(
        db,
        story_id,
    )

    return [
        action_to_list_item(
            db,
            action,
        )
        for action in actions
    ]
