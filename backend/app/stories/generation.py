"""Scene capability composition; no vendor or credential knowledge in Story services."""
from app.llm.resolver import resolve_adapter
from app.stories.generator import StoryGenerator


def get_story_generator(db, user_id: str) -> StoryGenerator:
    return resolve_adapter(db, user_id, "creative_writer")
