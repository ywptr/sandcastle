"""Optional generation composition; importing the API never requires an AI SDK or key."""
import os
from functools import lru_cache

from fastapi import HTTPException

from app.stories.generator import StoryGenerator


@lru_cache(maxsize=1)
def get_story_generator() -> StoryGenerator:
    if not os.getenv("OPENAI_API_KEY") or not os.getenv("SANDCASTLE_TEXT_MODEL"):
        raise HTTPException(503, "Scene generation is not enabled. You can create scenes manually.")
    try:
        from app.stories.adapters.openai_generator import OpenAIStoryGenerator
    except ImportError:
        raise HTTPException(503, "Scene generation is unavailable. You can create scenes manually.")
    return OpenAIStoryGenerator()
