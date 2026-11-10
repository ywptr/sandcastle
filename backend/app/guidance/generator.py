from dataclasses import dataclass, field
from typing import Protocol
from app.guidance.schemas import GuidanceProfileInput, Suggestion


@dataclass(frozen=True)
class NarrativeGuidanceContext:
    story_id: str
    title: str
    premise: str | None
    objective: str | None
    canon: list[dict]
    recent_scenes: list[dict]
    universe: dict | None
    profile: GuidanceProfileInput
    feedback: dict | None
    additional_instruction: str | None
    constraints: tuple[str, ...]
    language: str | None = None
    primary_genre: str | None = None
    secondary_genres: list[str] = field(default_factory=list)


class NarrativeSuggestionGenerator(Protocol):
    async def suggest(self, context: NarrativeGuidanceContext, *, count: int) -> list[Suggestion]: ...


class DeterministicSuggestionGenerator:
    """Conservative planning scaffolds, not a claim to understand arbitrary prose."""
    async def suggest(self, context: NarrativeGuidanceContext, *, count: int) -> list[Suggestion]:
        if context.language not in (None, "und", "en"):
            from app.guidance.localized import localized_choices
            choices = localized_choices(context)
            return [Suggestion(id=str(i + 1), title=title, text=text)
                    for i, (title, text) in enumerate(choices[:count])]
        if context.profile.audience == "child":
            choices = [
                ("One small step", "Let a character try one small, safe step toward the story's goal. Use simple words and a gentle tone."),
                ("Look closely", "Have a character look again at a detail already in the story. Ask a simple question without changing established facts."),
                ("Share a feeling", "Pause so a character can share a feeling or ask for help with the current problem."),
                ("Make a choice", "Offer a small choice using what the characters already know. Keep its consequences easy to understand."),
                ("A quiet moment", "Return to a familiar place for a calm moment before continuing the current goal."),
            ]
        elif context.profile.audience == "teen":
            choices = [
                ("Choose a next step", "Let a character choose how to pursue the existing goal, weighing an age-appropriate personal cost."),
                ("Question an assumption", "Revisit an unresolved detail from the recent scenes. Let a character ask what it means before deciding anything new."),
                ("Explore a response", "Pause on a character's feelings about the latest events and how to express them without assuming new relationships."),
                ("Consider a consequence", "Explore a plausible consequence of an existing choice, leaving uncertain facts open for review."),
                ("Reassess the goal", "Give a character space to reconsider the current approach while keeping the story's objective and established facts intact."),
            ]
        else:
            choices = [
                ("Advance the goal", "Choose a concrete next step toward the established objective, considering the emotional cost without assuming new facts."),
                ("Revisit an open question", "Examine an unresolved detail from recent scenes. Offer a cautious interpretation rather than an unsupported revelation."),
                ("Explore the aftermath", "Pause on a character's response to the latest events and the tension between personal needs and the existing goal."),
                ("Weigh a consequence", "Explore a consequence of an established choice, respecting known capabilities and leaving uncertain outcomes open."),
                ("Change the approach", "Let a character reconsider how to pursue the same objective, using existing knowledge rather than new powers or resources."),
            ]
        if context.primary_genre or context.secondary_genres:
            genres = ", ".join([context.primary_genre] if context.primary_genre else [])
            genres = ", ".join(filter(None, [genres, ", ".join(context.secondary_genres)]))
            choices = [(title, text + f" Tone/pacing: {genres}; preserve Canon.") for title, text in choices]
        # General/mild/mature never imply that explicitness is desirable. No raw
        # source, feedback or free-text instructions are echoed as plot facts.
        return [Suggestion(id=str(index + 1), title=title, text=text) for index, (title, text) in enumerate(choices[:count])]


def get_suggestion_generator() -> NarrativeSuggestionGenerator:
    return DeterministicSuggestionGenerator()
