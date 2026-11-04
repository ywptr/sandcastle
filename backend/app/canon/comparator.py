"""Conservative comparison: scalar contradictions are explicit; prose needs adjudication."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Literal, Protocol
import unicodedata
import re

from app.canon.extractor import ExtractedCanonFact
from app.db.models.canon_entry import CanonEntry

Classification = Literal["new", "consistent", "conflict", "uncertain"]


def normalize(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


@dataclass(frozen=True)
class Comparison:
    classification: Classification
    reasoning: str


class SemanticCanonComparator(Protocol):
    def compare(self, candidate: ExtractedCanonFact, approved_facts: list[dict]) -> Comparison:
        ...


def _scalar(key: str, value: str):
    value = normalize(value)
    if key in {"age", "height_cm"}:
        try:
            number = Decimal(value)
            return number if number.is_finite() and number >= 0 else None
        except InvalidOperation:
            return None
    if key == "alive":
        return {"true": True, "false": False}.get(value)
    if key in {"eye_color", "hair_color"}:
        value = {"grey": "gray", "blonde": "blond"}.get(value, value)
        return value if value in {"green", "blue", "brown", "hazel", "amber", "gray", "black", "red", "white", "silver", "blond"} else None
    return None


def compare_fact(
    fact: ExtractedCanonFact, approved: list[CanonEntry], *, unresolved: bool = False,
    ambiguous_legacy: bool = False, semantic: SemanticCanonComparator | None = None,
) -> Comparison:
    if unresolved:
        return Comparison("uncertain", "Subject identity is unresolved or ambiguous; select an existing domain subject before approval.")
    if re.search(r"\b(?:maybe|might|perhaps|possibly|probably|apparently)\b", normalize(fact.value)):
        return Comparison("uncertain", "The proposed value contains ambiguous or tentative language.")
    if not fact.explicit:
        return Comparison("uncertain", "The proposal is inferred or ambiguous rather than an explicit fact.")
    if ambiguous_legacy:
        return Comparison("uncertain", "Relevant legacy Canon has no stable subject identity; it cannot safely be assigned to this subject.")
    key = normalize(fact.key)
    scalar_keys = {"age", "height_cm", "alive", "eye_color", "hair_color"}
    proposed = _scalar(key, fact.value)
    if key in scalar_keys and proposed is None:
        return Comparison("uncertain", "The scalar value cannot be normalized safely.")
    if not approved:
        return Comparison("new", "No approved Canon fact exists for this subject and key.")
    if key in scalar_keys:
        existing = [_scalar(key, entry.value) for entry in approved]
        if any(value is None for value in existing):
            return Comparison("uncertain", "Existing Canon contains values that cannot be normalized safely.")
        if all(value == proposed for value in existing):
            return Comparison("consistent", "The normalized scalar value agrees with approved Canon.")
        return Comparison("conflict", "The scalar value contradicts current approved Canon for this subject and key.")
    if all(normalize(entry.value) == normalize(fact.value) for entry in approved):
        return Comparison("consistent", "The normalized statement agrees with approved Canon.")
    if semantic is not None:
        decision = semantic.compare(fact, [{"id": entry.canon_entry_id, "value": entry.value} for entry in approved])
        if decision.classification in {"consistent", "conflict", "uncertain"} and decision.reasoning.strip():
            return decision
    return Comparison("uncertain", "Different unstructured statements may be compatible; semantic adjudication or explicit human review is required.")
