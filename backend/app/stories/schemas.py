from datetime import datetime

from pydantic import BaseModel, Field, model_validator
from app.stories.metadata import Language, Genre, SecondaryGenres, validate_genres

from app.validation import InputModel, Name, PatchModel


class StoryMetadata(InputModel):
    language: Language | None = None
    primary_genre: Genre | None = None
    secondary_genres: SecondaryGenres = Field(default_factory=list)

    @model_validator(mode="after")
    def genres_valid(self):
        validate_genres(self.primary_genre, self.secondary_genres)
        return self


class StoryCreate(StoryMetadata):
    title: Name
    premise: str | None = None
    objective: str | None = None


class StoryResponse(BaseModel):
    story_id: str
    user_id: str
    title: str
    premise: str | None
    objective: str | None
    language: Language | None
    primary_genre: Genre | None
    secondary_genres: SecondaryGenres
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }


class StoryUpdate(PatchModel):
    nullable_fields = {"premise", "objective", "language", "primary_genre"}
    language: Language | None = None
    primary_genre: Genre | None = None
    secondary_genres: SecondaryGenres | None = None
    title: Name | None = None
    premise: str | None = None
    objective: str | None = None
