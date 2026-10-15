from sqlalchemy.orm import Session

from app.authority.port import (
    AuthorityContext,
    AuthorityEvaluator,
)
from app.canon.service import list_canon_entries
from app.db.models import (
    AuthorityDecision,
    Story,
    StoryAction,
)


def build_authority_context(
    db: Session,
    story: Story,
) -> AuthorityContext:
    entries = list_canon_entries(
        db,
        story.story_id,
    )

    canon_entries = [
        {
            "type": entry.type,
            "key": entry.key,
            "value": entry.value,
            "status": entry.status,
        }
        for entry in entries
    ]

    return AuthorityContext(
        story_id=story.story_id,
        objective=story.objective,
        canon_entries=canon_entries,
    )


def create_story_action(
    db: Session,
    *,
    story: Story,
    action_type: str,
    request: str,
) -> StoryAction:
    action = StoryAction(
        story_id=story.story_id,
        action_type=action_type,
        request=request,
        status="pending",
    )

    db.add(action)
    db.commit()
    db.refresh(action)

    return action


def evaluate_story_action(
    db: Session,
    *,
    story: Story,
    action: StoryAction,
    evaluator: AuthorityEvaluator,
) -> AuthorityDecision:
    context = build_authority_context(
        db,
        story,
    )

    result = evaluator.evaluate(
        action_type=action.action_type,
        request=action.request,
        context=context,
    )

    decision = AuthorityDecision(
        action_id=action.action_id,
        outcome=result.outcome,
        reason=result.reason,
        confidence=result.confidence,
        evaluator=evaluator.__class__.__name__,
    )

    action.status = "evaluated"

    db.add(decision)
    db.commit()
    db.refresh(decision)

    return decision