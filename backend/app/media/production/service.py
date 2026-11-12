"""Narrative interpretation/review/approval; never executes media or changes story content."""
import hashlib
import json
import logging
from uuid import uuid4
from fastapi import HTTPException
from pydantic import BaseModel, ValidationError
from app.llm.errors import ProviderFailed, ProviderIncomplete, ProviderOutputInvalid
from app.media.production.diagnostics import TranslationFailed, schema_reason
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from app.db.models import ApprovedMediaAdaptation, CanonCandidate, Scene, Story
from app.canon.schemas import CanonEntryResponse
from app.guidance.schemas import GuidanceProfileInput
from app.guidance.service import get_profile
from app.media.errors import InvalidMediaIntent, MediaDomainNotFound
from app.media.service import _require_story, _select_visual_context
from app.media.schemas import SceneImageOptions, MediaPlan
from app.media.production.compiler import compile_instructions, compile_manifest, plan_fingerprint
from app.media.production.schemas import (ApprovedProduction, CompiledProduction, ContinuityContext, MediaProductionPlan,
    ProductionProposal, ProductionWarning, units)
from app.media.production.translator import NarrativeMediaContext
from app.stories.scene_service import get_scene
from app.stories.scene_schemas import SceneResponse
from app.stories.schemas import StoryCreate
from app.workflows.service import read_workflow
from app.world.schemas import CharacterResponse, PlaceResponse


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def source_digest(scene):
    return digest({"content": scene.content, "title": scene.title})


def binding_context(db, story_id, user_id, references):
    """Project current and pinned binding relationships, never locators/bytes/arbitrary metadata."""
    from app.db.models import ReferenceBinding, CanonObjectVersion
    from app.canon.library_service import references as canon_references
    targets = {row.reference_id: (row.target_type, row.target_id) for row in db.scalars(
        select(ReferenceBinding).where(ReferenceBinding.story_id == story_id, ReferenceBinding.user_id == user_id))}
    for pin in canon_references(db, story_id):
        version = db.get(CanonObjectVersion, pin.canon_version_id)
        for visual in version.data["visuals"]:
            targets.setdefault(visual["binding_id"], (pin.target_type, pin.target_id))
    result = []
    for ref in references:
        if ref.kind == "artifact" and ref.binding_id:
            if ref.binding_id not in targets:
                raise InvalidMediaIntent("Reference binding context is unavailable")
            target_type, target_id = targets[ref.binding_id]
            result.append(dict(binding_id=ref.binding_id, artifact_id=ref.reference_id, target_type=target_type,
                target_id=target_id, role=ref.role))
    return result


def build_context(db, story_id, scene_id, user_id, target_format, instruction=None, output_language=None):
    story = _require_story(db, story_id, user_id)
    scene = get_scene(db, story_id, scene_id)
    if scene is None:
        raise MediaDomainNotFound("Scene not found in Story")
    if not scene.content.strip() or len(scene.content) > 40000:
        raise InvalidMediaIntent("Production translation requires a nonblank Scene of at most 40,000 characters")
    workflow = read_workflow(db, story_id, user_id)
    options = SceneImageOptions(**workflow["configuration"]["references"])
    characters, places, canon, references = _select_visual_context(db, story, options)
    profile = get_profile(db, story_id, user_id)
    continuity = ContinuityContext(
        story=StoryCreate(**{key: getattr(story, key) for key in StoryCreate.model_fields}),
        characters=[CharacterResponse.model_validate(c) for c in characters],
        places=[PlaceResponse.model_validate(p) for p in places],
        canon=[CanonEntryResponse.model_validate(c) for c in canon], references=references,
        reference_bindings=binding_context(db, story_id, user_id, references),
        guidance=GuidanceProfileInput(**profile.model_dump(exclude={"story_id", "created_at", "updated_at"})),
        workflow_configuration=workflow["configuration"])
    context_json = continuity.model_dump(mode="json")
    if len(json.dumps(context_json, ensure_ascii=False)) > 160000:
        raise InvalidMediaIntent("Production context exceeds the initial 160,000-character limit")
    return NarrativeMediaContext(story_id, SceneResponse.model_validate(scene), continuity, target_format,
        workflow, source_digest(scene), digest(context_json), instruction, output_language)


def validate_proposal(context, proposal):
    if proposal.production.target_format != context.target_format:
        raise InvalidMediaIntent("Production format does not match the requested format")
    character_ids = {c.character_id for c in context.continuity.characters}
    place_ids = {p.place_id for p in context.continuity.places}
    artifacts = {r.reference_id for r in context.continuity.references if r.kind in {"artifact", "generated_artifact", "uploaded_artifact"}}
    for beat in units(proposal.production):
        if not beat.source_excerpt.strip() or beat.source_excerpt not in context.scene.content:
            raise InvalidMediaIntent("Each production beat needs an exact excerpt from the source Scene")
        if not set(beat.character_ids) <= character_ids:
            raise InvalidMediaIntent("Production contains an unavailable Character ID")
        if not set(beat.place_ids) <= place_ids:
            raise InvalidMediaIntent("Production contains an unavailable Place ID")
        if not set(beat.artifact_ids) <= artifacts:
            raise InvalidMediaIntent("Production contains an unavailable Artifact reference")
        unbound = {ref.reference_id for ref in context.continuity.references if ref.kind == "artifact" and not ref.binding_id}
        applicable = unbound | {binding.artifact_id for binding in context.continuity.reference_bindings if
            binding.target_type == "story" or (binding.target_type == "character" and binding.target_id in beat.character_ids)
            or (binding.target_type == "place" and binding.target_id in beat.place_ids)}
        if not set(beat.artifact_ids) <= applicable:
            raise InvalidMediaIntent("Artifact reference binding does not match this beat's selected subjects")


def add_context_warnings(db, context, plan):
    warnings = []
    if not context.continuity.places:
        warnings.append(ProductionWarning(code="unclear_location", message="No Place record is selected. Review the intended location."))
    if any(not c.appearance for c in context.continuity.characters):
        warnings.append(ProductionWarning(code="missing_visual_information", message="Some Characters have no saved appearance. Review visual consistency before execution."))
    pending = db.scalar(select(func.count()).select_from(CanonCandidate).where(CanonCandidate.story_id == context.story_id,
        CanonCandidate.status == "pending", CanonCandidate.classification.in_(["conflict", "uncertain"])))
    if pending:
        warnings.append(ProductionWarning(code="continuity_uncertainty", message="Pending uncertain or conflicting Canon proposals exist. Review Canon; this plan does not approve or resolve them."))
    seen = set()
    plan.warnings = [item for item in [*warnings, *plan.warnings] if not ((item.code, item.message) in seen or seen.add((item.code, item.message)))][:20]
    return plan


logger = logging.getLogger(__name__)

# Only these application-owned messages may enter diagnostics. Never log arbitrary exception text.
DOMAIN_RULES = {
    "Production format does not match the requested format": "wrong_target_format",
    "Each production beat needs an exact excerpt from the source Scene": "source_excerpt_not_exact",
    "Production contains an unavailable Character ID": "unavailable_character_id",
    "Production contains an unavailable Place ID": "unavailable_place_id",
    "Production contains an unavailable Artifact reference": "unavailable_artifact_id",
    "Artifact reference binding does not match this beat's selected subjects": "artifact_binding_mismatch",
}


def validate_narrative_language(proposal, language):
    from app.languages.service import validate_output
    values = [proposal.summary, *(getattr(beat, field, "") for beat in units(proposal.production) for field in ("dialogue", "caption", "voiceover", "on_screen_text"))]
    statuses = [validate_output(text, language) for text in values if text.strip()]
    return "verified" if statuses and all(status == "verified" for status in statuses) else "unverified_short_or_ambiguous"


async def translate_scene(db, context, translator):
    category, reason = "unexpected_translation_failure", "internal_error"
    try:
        raw = await translator.translate(context)
        proposal = ProductionProposal.model_validate(raw.model_dump() if isinstance(raw, BaseModel) else raw)
        validate_proposal(context, proposal)
        from app.languages.service import production_language, validate_output
        resolution = production_language(context.continuity.story.language, context.output_language)
        validation = validate_narrative_language(proposal, resolution["language"])
        plan = MediaProductionPlan(output_language=context.output_language, language_context={"production":resolution,"validation":validation},**proposal.model_dump(), story_id=context.story_id, scene_id=context.scene.scene_id,
            target_format=context.target_format, source_digest=context.source_digest, context_digest=context.context_digest,
            continuity_context=context.continuity, instruction=context.instruction)
        add_context_warnings(db, context, plan)
        plan.compiled_instructions = compile_instructions(plan)
        return plan
    except TranslationFailed as error:
        category, reason = error.category, error.reason
    except ProviderIncomplete:
        category, reason = "provider_incomplete", "response_not_completed"
    except ProviderOutputInvalid:
        category, reason = "provider_structured_output_invalid", "credential_output_rejected"
    except ProviderFailed:
        category, reason = "provider_request_failed", "request_failed"
    except ValidationError as error:
        category, reason = "schema_validation_failed", schema_reason(error)
    except InvalidMediaIntent as error:
        category, reason = "domain_validation_failed", DOMAIN_RULES.get(str(error), "invalid_domain_proposal")
    except Exception:
        pass
    # Metadata comes from bounded settings, not upstream response text. Suppress credential collisions.
    provider = {"OpenAINarrativeMediaTranslator": "openai", "AnthropicNarrativeMediaTranslator": "anthropic",
        "GoogleNarrativeMediaTranslator": "google"}.get(type(translator).__name__, "unknown")
    model = getattr(translator, "model", "unknown")
    key = getattr(translator, "_api_key", None)
    if not isinstance(model, str) or len(model) > 255 or (key and key in model):
        model = "redacted"
    logger.warning("Narrative translation failed category=%s reason=%s provider=%s model=%r target_format=%s story_id=%s scene_id=%s",
        category, reason, provider, model, context.target_format, context.story_id, context.scene.scene_id)
    raise HTTPException(502, "Narrative translation failed or returned an invalid plan. No plan was saved.") from None


def review_plan(db, story_id, scene_id, user_id, plan):
    if (plan.story_id, plan.scene_id) != (story_id, scene_id):
        raise InvalidMediaIntent("Production plan belongs to a different Story or Scene")
    context = build_context(db, story_id, scene_id, user_id, plan.target_format, plan.instruction, plan.output_language)
    if plan.source_digest != context.source_digest:
        raise HTTPException(409, "Scene changed since this plan was created. Create a new adaptation.")
    if plan.context_digest != context.context_digest or plan.continuity_context != context.continuity:
        raise HTTPException(409, "Story, Canon, references, or guidance changed. Create a new adaptation.")
    validate_proposal(context, plan)
    from app.languages.service import production_language, validate_output
    resolution = production_language(context.continuity.story.language, plan.output_language)
    validate_narrative_language(plan, resolution["language"])
    if plan.overrides and context.workflow["difficulty"] not in {"difficult", "impossible"}:
        raise InvalidMediaIntent("Explicit instruction overrides require Difficult or Impossible difficulty")
    # Never trust client compiler output, and never let overrides replace authoritative context.
    plan = MediaProductionPlan.model_validate(plan.model_dump())
    plan.language_context = {"production":resolution,"validation":validate_narrative_language(plan, resolution["language"])}
    add_context_warnings(db, context, plan)
    plan.compiled_instructions = compile_instructions(plan)
    return CompiledProduction(plan=plan, manifest=compile_manifest(plan))


def owned_row(db, user_id, adaptation_id):
    row = db.scalar(select(ApprovedMediaAdaptation).where(ApprovedMediaAdaptation.adaptation_id == adaptation_id,
        ApprovedMediaAdaptation.user_id == user_id))
    if row is None:
        raise MediaDomainNotFound("Approved adaptation not found")
    _require_story(db, row.story_id, user_id)
    return row


def approval_view(db, row):
    scene = get_scene(db, row.story_id, row.scene_id)
    # Reading history must work even if current source is now too long/invalid for translation.
    changed = scene is None or source_digest(scene) != row.source_digest
    try:
        current = build_context(db, row.story_id, row.scene_id, row.user_id, row.target_format)
        context_changed = current.context_digest != row.context_digest
    except (InvalidMediaIntent, MediaDomainNotFound):
        context_changed = True
    return ApprovedProduction(adaptation_id=row.adaptation_id, revision=row.revision,
        plan=MediaProductionPlan.model_validate(row.plan_json), manifest=MediaPlan.model_validate(row.manifest_json),
        source_changed=changed, context_changed=context_changed, approved_at=row.approved_at)


def approve_plan(db, story_id, scene_id, user_id, plan):
    _require_story(db, story_id, user_id)
    if (plan.story_id, plan.scene_id) != (story_id, scene_id):
        raise InvalidMediaIntent("Plan belongs to a different Story or Scene")
    # Serialize revisions and synchronize with concurrent narrative writes.
    db.execute(select(Story).where(Story.story_id == story_id).with_for_update().execution_options(populate_existing=True))
    db.execute(select(Scene).where(Scene.scene_id == scene_id, Scene.story_id == story_id).with_for_update().execution_options(populate_existing=True))
    fingerprint = plan_fingerprint(plan)
    existing = db.scalar(select(ApprovedMediaAdaptation).where(ApprovedMediaAdaptation.user_id == user_id,
        ApprovedMediaAdaptation.plan_id == str(plan.plan_id), ApprovedMediaAdaptation.snapshot_digest == fingerprint))
    if existing:
        return approval_view(db, existing)
    reviewed = review_plan(db, story_id, scene_id, user_id, plan)
    # Include compiler-normalized warnings in idempotency identity.
    fingerprint = plan_fingerprint(reviewed.plan)
    revision = (db.scalar(select(func.max(ApprovedMediaAdaptation.revision)).where(
        ApprovedMediaAdaptation.scene_id == scene_id, ApprovedMediaAdaptation.target_format == plan.target_format)) or 0) + 1
    identity = str(uuid4())
    manifest = compile_manifest(reviewed.plan, adaptation_id=identity)
    row = ApprovedMediaAdaptation(adaptation_id=identity, user_id=user_id, story_id=story_id, scene_id=scene_id,
        target_format=plan.target_format, revision=revision, plan_id=str(plan.plan_id), source_digest=plan.source_digest,
        context_digest=plan.context_digest, snapshot_digest=fingerprint, plan_json=reviewed.plan.model_dump(mode="json"),
        manifest_json=manifest.model_dump(mode="json"), compiler_version=reviewed.plan.compiler_version)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Production approval changed concurrently. Refresh history before retrying.") from None
    except Exception:
        db.rollback()
        raise HTTPException(503, "Production approval could not be saved. Please retry.") from None
    return approval_view(db, row)


def list_approved(db, story_id, scene_id, user_id):
    _require_story(db, story_id, user_id)
    if get_scene(db, story_id, scene_id) is None:
        raise MediaDomainNotFound("Scene not found in Story")
    rows = db.scalars(select(ApprovedMediaAdaptation).where(ApprovedMediaAdaptation.user_id == user_id,
        ApprovedMediaAdaptation.story_id == story_id, ApprovedMediaAdaptation.scene_id == scene_id)
        .order_by(ApprovedMediaAdaptation.approved_at.desc(), ApprovedMediaAdaptation.revision.desc()))
    return [approval_view(db, row) for row in rows]
