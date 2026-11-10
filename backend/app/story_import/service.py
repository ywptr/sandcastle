import hashlib
import unicodedata

from pydantic import BaseModel

from app.story_import.analyzer import StoryImportAnalyzer
from app.story_import.schemas import Contradiction, Evidenced, ImportAnalysis, ImportAnalysisRequest, ImportProposal


class InvalidImportAnalysis(Exception):
    pass


def validate_evidence(value, source):
    if isinstance(value, Contradiction) and len(set(value.evidence)) < 2:
        raise ValueError("Contradictions require distinct supporting excerpts")
    if isinstance(value, Evidenced):
        if any(not excerpt.strip() or excerpt not in source for excerpt in value.evidence):
            raise ValueError("Evidence must be an exact nonblank source excerpt")
    if isinstance(value, BaseModel):
        for name in type(value).model_fields:
            validate_evidence(getattr(value, name), source)
    elif isinstance(value, list):
        for item in value:
            validate_evidence(item, source)


def deduplicate_entities(items):
    # Only exact normalized names are merged; no guessed alias/identity resolution.
    result = []
    seen = {}
    for item in items:
        key = " ".join(unicodedata.normalize("NFKC", item.name).casefold().split())
        if key not in seen:
            seen[key] = item
            result.append(item)
        elif item.model_dump(exclude={"name", "evidence"}) != seen[key].model_dump(exclude={"name", "evidence"}):
            raise ValueError("Duplicate entity has incompatible attributes")
        else:
            seen[key].evidence = list(dict.fromkeys(seen[key].evidence + item.evidence))[:5]
    return result


async def analyze_import(request: ImportAnalysisRequest, analyzer: StoryImportAnalyzer) -> ImportProposal:
    try:
        raw = await analyzer.analyze(request)
        # Revalidate even model instances; adapters and fakes are not trusted schema authorities.
        proposal = ImportAnalysis.model_validate(raw.model_dump() if isinstance(raw, BaseModel) else raw)
        validate_evidence(proposal, request.content)
        proposal.characters = deduplicate_entities(proposal.characters)
        proposal.places = deduplicate_entities(proposal.places)
        for candidate in proposal.canon_candidates:
            candidate.as_extracted_fact()  # Reuse M7 validation without its persistence services.
    except Exception as error:
        raise InvalidImportAnalysis("Import analysis failed or returned an invalid proposal") from error
    return ImportProposal(**proposal.model_dump(), source_type=request.source_type,
        source_hash=hashlib.sha256(request.content.encode("utf-8")).hexdigest())
