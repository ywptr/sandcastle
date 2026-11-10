"""Pure semantic compilation. No credentials, provider-native JSON, storage, or execution."""
import hashlib
import json
from uuid import UUID, uuid5
from app.media.production.schemas import CompiledInstruction, units
from app.media.schemas import MediaContext, MediaPlan, MediaPurpose, MediaRequest, MediaType


def plan_fingerprint(plan):
    value = plan.model_dump(mode="json", exclude={"compiled_instructions", "created_at"})
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def compile_instructions(plan):
    context = plan.continuity_context
    overrides = {override.beat_number: override.instruction for override in plan.overrides}
    result = []
    for number, beat in enumerate(units(plan.production), 1):
        lines = [f"{plan.target_format} · beat {number}", f"Purpose: {beat.narrative_purpose}",
                 f"Source moment: {beat.source_excerpt}", f"Visual: {beat.visual_description}"]
        if plan.target_format == "webtoon":
            lines += [f"Framing: {beat.framing}", f"Reading order: {plan.production.reading_order}", f"Layout: {plan.production.layout_hint}",
                      f"Dialogue: {beat.dialogue}", f"Caption: {beat.caption}"]
        elif plan.target_format == "short_drama":
            lines += [f"Estimated duration: {beat.estimated_duration} seconds (planning estimate)", f"Shot scale: {beat.shot_scale}",
                      f"Camera: {beat.camera_direction}", f"Performance: {beat.performance_direction}", f"Dialogue: {beat.dialogue}",
                      f"Voiceover: {beat.voiceover}", f"Ambience: {beat.audio_or_ambience}", f"Audio direction: {plan.production.audio_direction}"]
        else:
            lines += [f"Estimated duration: {beat.duration} seconds (planning estimate)", f"On-screen text: {beat.on_screen_text}",
                      f"Voiceover: {beat.voiceover}", f"Transition: {beat.transition_hint}",
                      f"Text strategy: {plan.production.narration_text_strategy}", f"Visual strategy: {plan.production.visual_strategy}"]
        characters = [c.model_dump(include={"character_id", "name", "description", "appearance", "outfit", "personality"}) for c in context.characters if c.character_id in beat.character_ids]
        places = [p.model_dump(include={"place_id", "name", "description", "appearance", "atmosphere"}) for p in context.places if p.place_id in beat.place_ids]
        authority_start = len(lines)
        lines += ["Character context: " + json.dumps(characters, ensure_ascii=False, sort_keys=True),
                  "Place context: " + json.dumps(places, ensure_ascii=False, sort_keys=True),
                  "Continuity constraints (approved Canon; do not change):"]
        lines += [f"- [{c.type}] {c.key}: {c.value}" for c in context.canon]
        lines += [*plan.continuity_notes, *beat.continuity_notes,
                  f"Audience: {context.guidance.audience}; maturity ceiling: {context.guidance.maturity_rating}",
                  f"Story language context: {context.story.language or 'retain source language'}; preserve reviewed dialogue/text exactly, including explicitly requested language changes.",
                  "Exclusions: no invented events, identities, outcomes, capabilities, or unreviewed dialogue; preserve uncertainty.",
                  "Artifact references are metadata identifiers only: " + ", ".join(beat.artifact_ids)]
        compiled = "\n".join(lines)
        override = overrides.get(number)
        # Overrides replace only the presentation instruction; authoritative context is appended.
        effective = compiled if override is None else "EXPLICIT PRESENTATION OVERRIDE:\n" + override + "\n\nAUTHORITATIVE CONTEXT:\n" + "\n".join(lines[authority_start:])
        result.append(CompiledInstruction(beat_number=number, compiled=compiled, override=override, effective=effective))
    return result


def compile_manifest(plan, *, adaptation_id=None):
    fingerprint = plan_fingerprint(plan)
    identity = adaptation_id or str(uuid5(plan.plan_id, fingerprint))
    compiled = compile_instructions(plan)
    requests = []
    for number, (beat, instruction) in enumerate(zip(units(plan.production), compiled), 1):
        refs = [ref for ref in plan.continuity_context.references if
                (ref.kind in {"character", "outfit"} and ref.reference_id in beat.character_ids)
                or (ref.kind == "place" and ref.reference_id in beat.place_ids)
                or (ref.kind in {"artifact", "generated_artifact", "uploaded_artifact"} and ref.reference_id in beat.artifact_ids)]
        is_image = plan.target_format == "webtoon"
        requests.append(MediaRequest(media_request_id=str(uuid5(UUID(identity), str(number))),
            media_type=MediaType.IMAGE if is_image else MediaType.VIDEO,
            purpose=MediaPurpose.COMIC_PANEL if is_image else MediaPurpose.VIDEO_SCENE,
            prompt=instruction.effective, story_id=plan.story_id, scene_id=plan.scene_id, references=refs,
            aspect_ratio=plan.continuity_context.workflow_configuration.media.aspect_ratio if is_image else "9:16",
            context=MediaContext(adaptation_id=identity, production_format=plan.target_format, production_beat_number=number,
                panel_number=number if is_image else None, panel_count=len(compiled) if is_image else None,
                estimated_duration_seconds=None if is_image else (beat.estimated_duration if plan.target_format == "short_drama" else beat.duration),
                canon_entry_ids=[c.canon_entry_id for c in plan.continuity_context.canon]), created_at=plan.created_at))
    return MediaPlan(media_plan_id=identity, story_id=plan.story_id, requests=requests, created_at=plan.created_at)
