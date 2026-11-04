"""Small explicit-fact grammar. Unsupported prose is left for manual proposals."""
import re

from app.canon.extractor import ExtractedCanonFact

# Names are resolved to existing stable IDs by the candidate service, never created here.
_NAME = r"(?P<name>[\w][\w '’-]*?)"
_PATTERNS = (
    (_NAME + r" has (?P<value>\w+) eyes[.!]?", "character", "physical_trait", "eye_color"),
    (_NAME + r" has (?P<value>\w+) hair[.!]?", "character", "physical_trait", "hair_color"),
    (_NAME + r" is (?P<value>\d+) years old[.!]?", "character", "age", "age"),
    (_NAME + r" is (?P<value>alive|dead)[.!]?", "character", "state", "alive"),
    (_NAME + r" is (?P<value>brave|shy|curious|gentle|cautious|kind|reckless)[.!]?", "character", "personality", "personality"),
    (_NAME + r" is married to (?P<value>.+?)[.!]?", "character", "relationship", "spouse"),
    (_NAME + r" owns (?P<value>.+?)[.!]?", "character", "possession", "possession"),
    (_NAME + r" became (?P<value>.+?)[.!]?", "character", "state", "role"),
    (_NAME + r" is controlled by (?P<value>.+?)[.!]?", "place", "ownership", "control"),
    (_NAME + r" wears (?P<value>.+?)[.!]?", "character", "possession", "outfit"),
    (_NAME + r" is (?:a|an) (?P<value>.+?)[.!]?", "character", "role", "role"),
    (_NAME + r" can (?P<value>.+?)[.!]?", "character", "capability", "capability"),
    (_NAME + r" has (?:a|an) (?P<value>.+?) climate[.!]?", "place", "environment", "climate"),
)


class DeterministicCanonExtractor:
    async def extract(self, *, story_title: str, scene_content: str) -> list[ExtractedCanonFact]:
        facts = []
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", scene_content) if part.strip()]
        for sentence in sentences:
            labeled = re.fullmatch(r"(Rule|Event|Timeline) ([\w -]+):\s*(.+)", sentence, re.IGNORECASE)
            if labeled:
                kind, key, value = labeled.groups()
                kind = kind.casefold()
                facts.append(ExtractedCanonFact(
                    type="world" if kind == "rule" else kind, fact_type=kind,
                    key=key.strip().casefold().replace(" ", "_"), value=value,
                    evidence=sentence, confidence=1.0,
                ))
                continue
            for pattern, subject_type, fact_type, key in _PATTERNS:
                match = re.fullmatch(pattern, sentence, re.IGNORECASE)
                if not match:
                    continue
                name, value = match.group("name"), match.group("value").rstrip(".!?")
                if key == "alive":
                    value = "true" if value.casefold() == "alive" else "false"
                facts.append(ExtractedCanonFact(
                    type=subject_type, subject_name=name.strip(), fact_type=fact_type,
                    key=key, value=value, evidence=sentence, confidence=1.0,
                ))
                break
        return facts


def get_canon_extractor():
    return DeterministicCanonExtractor()
