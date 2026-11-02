from sqlalchemy.orm import Session

from app.canon.extractor import CanonExtractor
from app.db.models.canon_candidate import (
    CanonCandidate,
)
from app.db.models.scene import Scene
from app.db.models.story import Story


def list_candidates(
    db: Session,
    story_id: str,
) -> list[CanonCandidate]:
    return (
        db.query(CanonCandidate)
        .filter(
            CanonCandidate.story_id == story_id,
            CanonCandidate.status == "proposed",
        )
        .order_by(
            CanonCandidate.created_at.asc()
        )
        .all()
    )


async def extract_candidates(
    db: Session,
    *,
    story: Story,
    scene: Scene,
    extractor: CanonExtractor,
) -> list[CanonCandidate]:
    facts = await extractor.extract(
        story_title=story.title,
        scene_content=scene.content,
    )

    candidates = [
        CanonCandidate(
            story_id=story.story_id,
            scene_id=scene.scene_id,
            type=fact.type,
            key=fact.key,
            value=fact.value,
        )
        for fact in facts
    ]

    db.add_all(candidates)
    db.commit()

    for candidate in candidates:
        db.refresh(candidate)

    return candidates