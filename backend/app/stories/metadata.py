"""Shared bounded Story/import vocabulary. Expand codes deliberately with UX support."""
from typing import Annotated, Literal
from pydantic import BeforeValidator, Field

LANGUAGE_NAMES = {"en": "English", "id": "Indonesian", "ja": "Japanese", "ko": "Korean",
                  "zh-CN": "Simplified Chinese", "fr": "French", "de": "German", "es": "Spanish",
                  "und": "Undetermined"}


def normalize_language(value):
    if isinstance(value, str):
        codes = {code.lower(): code for code in LANGUAGE_NAMES}
        return codes.get(value.strip().lower(), value)
    return value


Language = Annotated[Literal["en", "id", "ja", "ko", "zh-CN", "fr", "de", "es", "und"], BeforeValidator(normalize_language)]
Genre = Literal["fantasy", "science_fiction", "mystery", "thriller", "romance", "horror",
                "adventure", "drama", "comedy", "historical", "slice_of_life", "other", "unknown"]
SecondaryGenres = Annotated[list[Genre], Field(max_length=3)]


def validate_genres(primary, secondary):
    if len(secondary) != len(set(secondary)):
        raise ValueError("Secondary genres must be unique")
    if primary is not None and primary in secondary:
        raise ValueError("Secondary genres must not duplicate primary genre")


def creative_constraints(language, primary, secondary):
    rules = []
    if language and language != "und":
        rules.append(f"Write generated story content and suggestions in {LANGUAGE_NAMES[language]} ({language}), regardless of the user instruction or UI language. This is the resolved operation target (an explicit typed override takes precedence over saved Story language). Never update Story metadata from a generation request.")
    if primary or secondary:
        rules.append(f"Primary genre: {primary or 'unspecified'}; secondary genres: {', '.join(secondary) or 'none'}. Use as soft guidance for tone, pacing, plot suggestions and prose style. Genre is not Canon; never invent facts or override Canon to satisfy genre.")
    return tuple(rules)
