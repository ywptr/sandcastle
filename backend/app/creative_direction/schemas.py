from typing import Literal
from pydantic import Field
from app.validation import InputModel
from app.languages.service import LanguageOptions
from app.stories.schemas import StoryCreate, StoryMetadata
from app.stories.metadata import Language

Format = Literal["story", "webtoon", "short_drama", "story_reel"]
Rating = Literal["all_ages", "teen_13", "young_adult_16", "mature_18"]
Visual = Literal["match_style", "anime_2d", "korean_webtoon", "cinematic_realism", "illustrated_storybook", "painterly", "stylized_3d"]


class DirectionInput(InputModel):
    target_format: Format = "story"
    storytelling_style_id: str = Field(min_length=1, max_length=80)
    style_version: str = Field(min_length=1, max_length=20)
    audience_rating: Rating = "teen_13"
    visual_style: Visual = "match_style"
    cultural_setting: str | None = Field(default=None, max_length=200)
    historical_era: str | None = Field(default=None, max_length=200)
    tone: str | None = Field(default=None, max_length=200)
    tropes: list[str] = Field(default_factory=list, max_length=12)
    expected_revision: int = Field(default=0, ge=0)


class RecommendationInput(LanguageOptions):
    idea: str = Field(min_length=1, max_length=8000)
    target_format: Format
    language: Language | None = None


class Recommendation(StoryMetadata):
    target_format: Format
    storytelling_style_id: str = Field(min_length=1, max_length=80)
    audience_rating: Rating
    visual_style: Visual
    tone: str | None = Field(default=None, max_length=200)
    rationale: str = Field(min_length=1, max_length=1200)
    warnings: list[str] = Field(default_factory=list, max_length=12)


class RecommendationResponse(Recommendation):
    language_context: dict | None = None


class StartStory(InputModel):
    language_mode: Literal["automatic", "explicit"] | None = None
    story: StoryCreate
    creative_direction: DirectionInput
