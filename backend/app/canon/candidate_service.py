"""Canon proposals and explicit review; extraction/analysis never mutate approved Canon."""
import hashlib
import json

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.canon.comparator import Comparison, SemanticCanonComparator, compare_fact, normalize
from app.canon.extractor import CanonExtractor, ExtractedCanonFact
from app.canon.candidate_schemas import CandidateApproval, ContinuityReport, ManualCandidate
from app.canon.service import list_canon_entries
from app.db.models.canon_candidate import CanonCandidate
from app.db.models.canon_entry import CanonEntry
from app.db.models.story import Story
from app.db.types import utc_now
from app.media.errors import InvalidMediaIntent, MediaDomainNotFound
from app.stories.scene_service import get_scene
from app.stories.service import get_story
from app.world.service import get_character, get_place, list_characters, list_places


class CandidateConflict(ValueError):
    pass


class ExtractionFailed(ValueError):
    pass


def require_story(db: Session, story_id: str, user_id: str, *, lock=False) -> Story:
    story = get_story(db, story_id, user_id)
    if story is None:
        raise MediaDomainNotFound("Story not found")
    if lock:
        db.execute(select(Story.story_id).where(Story.story_id == story_id).with_for_update())
    return story


def require_scene(db: Session, story_id: str, scene_id: str):
    scene = get_scene(db, story_id, scene_id)
    if scene is None:
        raise MediaDomainNotFound("Scene not found in story")
    return scene


def story_source(story: Story) -> str:
    return "\n".join(value for value in [story.premise, story.objective] if value)


def _hash(text: str) -> str:
    return hashlib.sha256(normalize(text).encode()).hexdigest()


def _resolve_subject(db: Session, story_id: str, fact: ExtractedCanonFact, *, strict=False):
    if fact.type not in {"character", "place"}:
        return None, fact.type not in {"world", "story", "timeline", "event"}
    getter = get_character if fact.type == "character" else get_place
    if fact.subject_id:
        subject = getter(db, story_id, fact.subject_id)
        if subject is None and strict:
            raise MediaDomainNotFound("Subject not found in story")
        return fact.subject_id if subject else None, subject is None
    subjects = list_characters(db, story_id) if fact.type == "character" else list_places(db, story_id)
    matches = [subject for subject in subjects if fact.subject_name and normalize(subject.name) == normalize(fact.subject_name)]
    if len(matches) != 1:
        return None, True
    return (matches[0].character_id if fact.type == "character" else matches[0].place_id), False


def _relevant(db: Session, candidate: CanonCandidate):
    approved = [entry for entry in list_canon_entries(db, candidate.story_id) if entry.status == "approved"]
    relevant, ambiguous = [], []
    key = normalize(candidate.key)
    getter = get_character if candidate.type == "character" else get_place
    subject = getter(db, candidate.story_id, candidate.subject_id) if candidate.type in {"character", "place"} and candidate.subject_id else None
    legacy_keys = set()
    if subject:
        subjects = list_characters(db, candidate.story_id) if candidate.type == "character" else list_places(db, candidate.story_id)
        slug = normalize(subject.name).replace(" ", "_")
        if sum(normalize(item.name).replace(" ", "_") == slug for item in subjects) == 1:
            legacy_keys.add(f"{candidate.type}.{slug}.{key}")
        legacy_keys.add(f"{candidate.type}.{candidate.subject_id}.{key}")
    for entry in approved:
        if {"location": "place", "rule": "world", "outfit": "character"}.get(entry.type, entry.type) != candidate.type:
            continue
        if entry.subject_id is not None:
            if entry.subject_id == candidate.subject_id and normalize(entry.key).replace(" ", "_") == key:
                relevant.append(entry)
        elif candidate.type in {"character", "place"}:
            if normalize(entry.key).replace(" ", "_") in legacy_keys:
                relevant.append(entry)
            elif normalize(entry.key).replace(" ", "_") == key:
                ambiguous.append(entry)
        elif normalize(entry.key).replace(" ", "_") == key:
            relevant.append(entry)
    return relevant, ambiguous


def _snapshot(entries):
    return [{"canon_entry_id": entry.canon_entry_id, "type": entry.type, "subject_id": entry.subject_id,
             "canon_version_id": getattr(entry, "canon_version_id", None),
             "fact_type": entry.fact_type, "key": entry.key, "value": entry.value, "status": entry.status}
            for entry in entries]


def analyze_candidate(db: Session, candidate: CanonCandidate, semantic: SemanticCanonComparator | None = None):
    fact = ExtractedCanonFact.model_validate({**candidate.extraction_data, "subject_id": candidate.subject_id,
                                              "type": candidate.type, "key": candidate.key, "value": candidate.value})
    resolved_id, unresolved = _resolve_subject(db, candidate.story_id, fact)
    candidate.subject_id = resolved_id
    relevant, ambiguous = _relevant(db, candidate)
    stale = False
    if candidate.source_kind == "scene":
        scene = get_scene(db, candidate.story_id, candidate.scene_id)
        stale = scene is None or _hash(scene.content) != candidate.source_hash
    elif candidate.source_kind == "story":
        story = db.get(Story, candidate.story_id)
        stale = story is None or _hash(story_source(story)) != candidate.source_hash
    if stale:
        decision = Comparison("uncertain", "Source content changed after extraction; extract again before approval.")
    elif fact.confidence is not None and fact.confidence < 0.5:
        decision = Comparison("uncertain", "Extraction confidence is too low for safe deterministic classification.")
    else:
        decision = compare_fact(fact, relevant, unresolved=unresolved, ambiguous_legacy=bool(ambiguous), semantic=semantic)
    candidate.classification = decision.classification
    candidate.reasoning = decision.reasoning
    candidate.comparison_snapshot = _snapshot(relevant + ambiguous)
    candidate.analyzed_at = utc_now()
    return relevant, stale


def _persist_facts(db, story, user_id, facts, source_kind, source_snapshot, scene_id=None):
    source_hash = _hash(source_snapshot)
    rows = []
    for fact in facts:
        subject_id, _ = _resolve_subject(db, story.story_id, fact, strict=True)
        payload = {"source": source_kind, "source_hash": source_hash, "scene_id": scene_id,
                   "type": fact.type, "subject_id": subject_id, "subject_name": normalize(fact.subject_name or ""),
                   "fact_type": normalize(fact.fact_type), "key": normalize(fact.key), "value": normalize(fact.value),
                   "evidence": normalize(fact.evidence)}
        dedup_key = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        existing = db.scalar(select(CanonCandidate).where(
            CanonCandidate.user_id == user_id, CanonCandidate.story_id == story.story_id, CanonCandidate.dedup_key == dedup_key,
        ))
        if existing:
            if existing.status == "pending":
                analyze_candidate(db, existing)
            if existing not in rows:
                rows.append(existing)
            continue
        row = CanonCandidate(
            user_id=user_id, story_id=story.story_id, scene_id=scene_id, type=fact.type,
            subject_id=subject_id, subject_name=fact.subject_name, fact_type=fact.fact_type,
            key=normalize(fact.key).replace(" ", "_"), value=fact.value, evidence=fact.evidence,
            source_kind=source_kind, source_snapshot=source_snapshot, source_hash=source_hash,
            dedup_key=dedup_key, extraction_data=fact.model_dump(), confidence=fact.confidence,
            reasoning="Awaiting analysis", status="pending",
        )
        db.add(row)
        analyze_candidate(db, row)
        db.flush()  # Makes duplicate facts within this extraction visible to the next lookup.
        rows.append(row)
    db.commit()
    return rows


async def extract_candidates(db: Session, *, story_id: str, user_id: str, extractor: CanonExtractor, scene_id: str | None = None):
    story = require_story(db, story_id, user_id)
    snapshot = require_scene(db, story_id, scene_id).content if scene_id else story_source(story)
    if not snapshot.strip():
        raise InvalidMediaIntent("Source content is empty")
    try:
        output = await extractor.extract(story_title=story.title, scene_content=snapshot)
        facts = TypeAdapter(list[ExtractedCanonFact]).validate_python(output)
        if len(facts) > 100 or any(normalize(fact.evidence) not in normalize(snapshot) for fact in facts):
            raise ValueError("Invalid extraction evidence or too many facts")
    except Exception as error:
        raise ExtractionFailed("Extractor did not return valid structured facts grounded in the source") from error
    require_story(db, story_id, user_id, lock=True)
    try:
        return _persist_facts(db, story, user_id, facts, "scene" if scene_id else "story", snapshot, scene_id)
    except Exception:
        db.rollback()
        raise


def propose_candidate(db: Session, *, story_id: str, user_id: str, proposal: ManualCandidate):
    story = require_story(db, story_id, user_id, lock=True)
    if proposal.scene_id:
        require_scene(db, story_id, proposal.scene_id)
    fact = ExtractedCanonFact.model_validate(proposal.model_dump(exclude={"scene_id"}))
    try:
        return _persist_facts(db, story, user_id, [fact], "manual", proposal.evidence, proposal.scene_id)[0]
    except Exception:
        db.rollback()
        raise


def list_candidates(db: Session, story_id: str, user_id: str, *, status=None, classification=None, scene_id=None):
    require_story(db, story_id, user_id)
    if scene_id:
        require_scene(db, story_id, scene_id)
    query = select(CanonCandidate).where(CanonCandidate.story_id == story_id, CanonCandidate.user_id == user_id)
    for column, value in [(CanonCandidate.status, status), (CanonCandidate.classification, classification), (CanonCandidate.scene_id, scene_id)]:
        if value is not None:
            query = query.where(column == value)
    return list(db.scalars(query.order_by(CanonCandidate.created_at, CanonCandidate.canon_candidate_id)))


def get_candidate(db: Session, story_id: str, candidate_id: str, user_id: str):
    require_story(db, story_id, user_id)
    candidate = db.scalar(select(CanonCandidate).where(
        CanonCandidate.canon_candidate_id == candidate_id, CanonCandidate.story_id == story_id, CanonCandidate.user_id == user_id,
    ))
    if candidate is None:
        raise MediaDomainNotFound("Canon candidate not found")
    return candidate


def reclassify_pending(db: Session, *, story_id: str, user_id: str, scene_id=None, semantic=None):
    require_story(db, story_id, user_id, lock=True)
    rows = list_candidates(db, story_id, user_id, status="pending", scene_id=scene_id)
    for candidate in rows:
        analyze_candidate(db, candidate, semantic)
    db.commit()
    return rows


def approve_candidate(db: Session, *, story_id: str, candidate_id: str, user_id: str, approval: CandidateApproval):
    require_story(db, story_id, user_id, lock=True)
    candidate = get_candidate(db, story_id, candidate_id, user_id)
    if candidate.status == "approved":
        return candidate
    if candidate.status != "pending":
        raise CandidateConflict("Rejected candidates cannot be approved")
    try:
        if approval.subject_id:
            fact = ExtractedCanonFact.model_validate({**candidate.extraction_data, "subject_id": approval.subject_id})
            candidate.subject_id, _ = _resolve_subject(db, story_id, fact, strict=True)
        relevant, stale = analyze_candidate(db, candidate)
        if stale:
            raise CandidateConflict("Source changed; extract a new proposal before approval")
        if candidate.type in {"character", "place"} and not candidate.subject_id:
            raise CandidateConflict("Resolve the subject to an existing Character or Place before approval")
        if candidate.type not in {"character", "place", "world", "story", "timeline", "event"}:
            raise InvalidMediaIntent("Unsupported subject type for approval")
        if candidate.classification == "conflict" and not approval.replace_conflicts:
            raise CandidateConflict("Approval requires explicit replace_conflicts consent")
        if candidate.classification == "uncertain" and not approval.accept_uncertain:
            raise CandidateConflict("Uncertain proposals require explicit accept_uncertain consent")
        if relevant and candidate.classification != "consistent" and not approval.replace_conflicts:
            raise CandidateConflict("Replacing current Canon requires explicit replace_conflicts consent")
        from app.canon.library_service import editable_reference, record_edit
        ref = None
        if candidate.classification != "consistent":
            ref = editable_reference(db, story_id, candidate.type, candidate.subject_id)
        if candidate.classification == "consistent" and relevant and db.get(CanonEntry, relevant[0].canon_entry_id) is not None:
            entry = db.get(CanonEntry, relevant[0].canon_entry_id)
        else:
            candidate.superseded_entry_ids = [entry.canon_entry_id for entry in relevant]
            for old in relevant:
                historical = db.get(CanonEntry, old.canon_entry_id)
                if historical is not None and historical.story_id == story_id:
                    historical.status = "superseded"
            entry = CanonEntry(story_id=story_id, type=candidate.type, subject_id=candidate.subject_id,
                               fact_type=candidate.fact_type, key=candidate.key, value=candidate.value, status="approved")
            db.add(entry)
            db.flush()
            record_edit(db, ref, fact={"key": candidate.key, "value": candidate.value, "fact_type": candidate.fact_type, "source_entry_id": entry.canon_entry_id})
        candidate.approved_canon_entry_id = entry.canon_entry_id
        candidate.status = "approved"
        candidate.reviewed_at = utc_now()
        candidate.review_note = approval.note
        db.commit()
        return candidate
    except Exception:
        db.rollback()
        raise


def reject_candidate(db: Session, *, story_id: str, candidate_id: str, user_id: str, note=None):
    require_story(db, story_id, user_id, lock=True)
    candidate = get_candidate(db, story_id, candidate_id, user_id)
    if candidate.status == "approved":
        raise CandidateConflict("Approved candidates cannot be rejected")
    if candidate.status == "pending":
        candidate.status = "rejected"
        candidate.reviewed_at = utc_now()
        candidate.review_note = note
        db.commit()
    return candidate


def continuity_report(db: Session, *, story_id: str, user_id: str, scene_id=None):
    rows = reclassify_pending(db, story_id=story_id, user_id=user_id, scene_id=scene_id)
    counts = {kind: sum(row.classification == kind for row in rows) for kind in ["new", "consistent", "conflict", "uncertain"]}
    return ContinuityReport(story_id=story_id, scene_id=scene_id, counts=counts, total=len(rows),
                            issues=[row for row in rows if row.classification in {"conflict", "uncertain"}])
