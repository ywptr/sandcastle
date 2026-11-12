from typing import Annotated, Literal

from pydantic import Field, StringConstraints, field_validator

from app.canon.extractor import ExtractedCanonFact
from app.validation import InputModel, Name

MAX_CONTENT_LENGTH = 40000
SourceType = Literal["summary", "draft", "notes"]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
Excerpt = Annotated[str, StringConstraints(min_length=1, max_length=500)]
from app.stories.metadata import Genre, Language, validate_genres
from pydantic import model_validator


class ImportAnalysisRequest(InputModel):
    content: Annotated[str, StringConstraints(min_length=1, max_length=MAX_CONTENT_LENGTH)]
    source_type: SourceType

    @field_validator("content")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Content must not be blank")
        return value  # Preserve the source exactly for evidence review.


class Evidenced(InputModel):
    evidence: list[Excerpt] = Field(min_length=1, max_length=5)


class ProposedStory(Evidenced):
    proposed_title: Name | None = None
    premise: Text | None = None
    objective: Text | None = None
    detected_language: Language
    primary_genre: Genre
    secondary_genres: list[Genre] = Field(default_factory=list, max_length=3)


    @model_validator(mode="after")
    def genres_valid(self):
        validate_genres(self.primary_genre, self.secondary_genres)
        return self


class ProposedCharacter(Evidenced):
    name: Name
    description: Text | None = None
    appearance: Text | None = None
    outfit: Text | None = None
    personality: Text | None = None


class ProposedPlace(Evidenced):
    name: Name
    description: Text | None = None
    appearance: Text | None = None
    atmosphere: Text | None = None


class ImportCanonCandidate(Evidenced):
    type: Literal["character", "place", "world", "timeline", "event", "story"]
    subject_name: Name | None = None
    fact_type: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    key: Name
    value: Text
    classification: Literal["explicit", "inferred", "uncertain", "conflicting"]
    reasoning: Text

    def as_extracted_fact(self) -> ExtractedCanonFact:
        """M7-compatible fact vocabulary; does not create a persisted candidate."""
        return ExtractedCanonFact(type=self.type, subject_name=self.subject_name,
            fact_type=self.fact_type, key=self.key, value=self.value,
            evidence="\n".join(self.evidence), explicit=self.classification == "explicit")


class ProposedEvent(Evidenced):
    description: Text
    kind: Literal["backstory", "current", "unresolved"]


class ProposedSequence(Evidenced):
    title: Name | None = None
    summary: Text


class UnresolvedThread(Evidenced):
    question: Text


class Contradiction(Evidenced):
    description: Text
    classification: Literal["clear", "uncertain"]
    # At least two supporting passages must be supplied for comparison.
    evidence: list[Excerpt] = Field(min_length=2, max_length=5)


class ImportAnalysis(InputModel):
    story: ProposedStory
    characters: list[ProposedCharacter] = Field(default_factory=list, max_length=50)
    places: list[ProposedPlace] = Field(default_factory=list, max_length=50)
    canon_candidates: list[ImportCanonCandidate] = Field(default_factory=list, max_length=100)
    events: list[ProposedEvent] = Field(default_factory=list, max_length=100)
    proposed_scenes: list[ProposedSequence] = Field(default_factory=list, max_length=50)
    proposed_episodes: list[ProposedSequence] = Field(default_factory=list, max_length=30)
    unresolved_threads: list[UnresolvedThread] = Field(default_factory=list, max_length=50)
    contradictions: list[Contradiction] = Field(default_factory=list, max_length=30)
    warnings: list[Text] = Field(default_factory=list, max_length=20)


class ImportProposal(ImportAnalysis):
    language_detection: dict | None = None
    source_type: SourceType
    source_hash: str
