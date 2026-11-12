from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.db.models.creative_direction import CreativeDirectionSnapshot
from app.db.models.story import Story
from app.stories.service import get_story
from app.creative_direction.registry import style_snapshot


def require_story(db, user_id, story_id):
    story = get_story(db, story_id, user_id)
    if story is None:
        raise HTTPException(404, "Story not found")
    return story


def latest(db, user_id, story_id):
    require_story(db, user_id, story_id)
    return db.scalar(select(CreativeDirectionSnapshot).where(CreativeDirectionSnapshot.story_id == story_id,
        CreativeDirectionSnapshot.user_id == user_id).order_by(CreativeDirectionSnapshot.revision.desc()).limit(1))


def view(row):
    return dict(direction_id=row.direction_id, story_id=row.story_id, revision=row.revision,
        direction=row.direction_json, style=row.style_snapshot, approved_at=row.approved_at.isoformat())


def append(db, user_id, story, data):
    style = style_snapshot(data.storytelling_style_id, data.style_version)
    if data.target_format not in style["supported_formats"]:
        raise HTTPException(422, "Style does not support this format")
    current = latest(db, user_id, story.story_id)
    revision = current.revision if current else 0
    if data.expected_revision != revision:
        raise HTTPException(409, "Creative Direction changed. Reload before approving a new revision.")
    values = data.model_dump(exclude={"expected_revision"})
    if any(len(t) > 120 or not t.strip() for t in values["tropes"]):
        raise HTTPException(422, "Invalid trope")
    values["language_at_approval"] = story.language
    row = CreativeDirectionSnapshot(story_id=story.story_id,user_id=user_id,revision=revision+1,
        direction_json=values,style_snapshot=style)
    db.add(row)
    return row


def commit(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Creative Direction changed. Reload before approving.") from None
    except Exception:
        db.rollback()
        raise HTTPException(503, "Creative Direction could not be saved. Please retry.") from None


def start(db, user_id, request):
    # Ordinary Story plus approved direction, in one transaction. No onboarding Story type.
    try:
        from app.languages.service import creation_language
        provenance = creation_language(request.story.premise, request.story.language, request.language_mode)
        story = Story(user_id=user_id, language_provenance=provenance, **request.story.model_dump())
        db.add(story)
        db.flush()
        append(db, user_id, story, request.creative_direction)
        commit(db)
        db.refresh(story)
        return story
    except Exception:
        db.rollback()
        raise
