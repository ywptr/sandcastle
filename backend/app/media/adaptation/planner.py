"""A narrow explicit-English planner; no provider policy or Canon mutations."""
from dataclasses import dataclass
import re
from typing import Protocol
from app.guidance.schemas import GuidanceProfileResponse
from app.media.schemas import Reference
from app.canon.comparator import compare_fact
from app.canon.extractor import ExtractedCanonFact
from app.db.models.canon_entry import CanonEntry
from app.media.adaptation.schemas import AdaptationOptions, AdaptedShot, AdaptationIssue, MediaAdaptationPlan

_PATTERNS = {
    "violence": r"\b(?:stab(?:s|bed|bing)?|kill(?:s|ed|ing)?|murder\w*|shoot\w*|shot|fight\w*|attack\w*|punch\w*|confrontation)\b",
    "intimacy": r"\b(?:intima\w*|sex\w*|naked|nud\w*|undress\w*|mak(?:e|es|ing) love|kiss\w*|embrac\w*)\b",
    "injury": r"\b(?:blood\w*|bleed\w*|wound\w*|injur\w*|gore|dismember\w*|corpse\w*)\b",
    "horror": r"\b(?:horror|terrify\w*|terrified|tortur\w*|monster\w*|nightmare\w*)\b",
    "substance_use": r"\b(?:drunk|alcohol|cocaine|heroin|overdose\w*|drug\w*|smok\w*|cigarette\w*)\b",
}


@dataclass(frozen=True)
class AdaptationContext:
    story_id: str
    scene_id: str
    scene_content: str
    profile: GuidanceProfileResponse
    characters: list[dict]
    places: list[dict]
    canon: list[dict]
    references: list[Reference]
    options: AdaptationOptions
    digest: str


class ShotPlanner(Protocol):
    def adapt(self, context: AdaptationContext) -> MediaAdaptationPlan: ...


def source_beats(content):
    # Exact spans, not rewritten summaries. Abbreviations/complex prose need semantic planning.
    for match in re.finditer(r"[^.!?\n]+(?:[.!?]+|(?=\n|$))", content):
        raw = match.group()
        if raw.strip():
            start = match.start() + len(raw) - len(raw.lstrip())
            end = match.end() - len(raw) + len(raw.rstrip())
            yield start, end, content[start:end]


def _issues(context, beat, start, end):
    issues = []
    for fact in context.canon:
        subjects = [item for item in context.characters if item["id"] == fact["subject_id"]]
        if not subjects and fact.get("subject_name"):
            subjects = [{"id": fact["subject_id"], "name": fact["subject_name"]}]
        if not subjects:
            continue
        key, value = fact["key"].casefold().rsplit(".", 1)[-1], fact["value"].casefold().strip()
        blocked = (key in {"can_walk", "can_run"} and value in {"false", "no"}) or (key in {"mobility", "capability"} and re.search(r"\b(?:cannot|can't|unable to) (?:walk|run)\b", value))
        for subject in subjects:
            name = re.escape(subject["name"])
            movement = r"(?:runs?|running|sprints?)" if key == "can_run" or re.search(r"(?:cannot|can't|unable to) run", value) else r"(?:runs?|walks?|running|walking|sprints?)"
            motion = re.search(r"\b" + name + r"\s+(?:(?:quickly|slowly|suddenly|is|was)\s+)*" + movement + r"\b", beat, re.I)
            active_dead = key == "alive" and value == "false" and re.search(r"\b" + name + r"\s+(?:runs?|walks?|speaks?|says|laughs?)\b", beat, re.I)
            scalar_patterns = {
                "eye_color": r" has (\w+) eyes\b", "hair_color": r" has (\w+) hair\b",
                "age": r" is (\d+) years old\b", "alive": r" is (alive|dead)\b",
            }
            scalar_conflict = False
            if key in scalar_patterns:
                explicit = re.search(r"\b" + name + scalar_patterns[key], beat, re.I)
                if explicit:
                    proposed = explicit.group(1)
                    if key == "alive":
                        proposed = "true" if proposed.casefold() == "alive" else "false"
                    comparison = compare_fact(ExtractedCanonFact(type="character", subject_id=subject["id"],
                        key=key, value=proposed, evidence=beat), [CanonEntry(value=fact["value"])])
                    scalar_conflict = comparison.classification == "conflict"
            if (blocked and motion) or active_dead or scalar_conflict:
                issues.append(AdaptationIssue(code="canon_conflict", message="Narrative beat conflicts with known subject continuity; review in Canon continuity before planning depiction.",
                    canon_entry_ids=[fact["id"]], source_start=start, source_end=end))
    return issues


class DeterministicShotPlanner:
    def adapt(self, context):
        shots, issues, detected = [], [], set()
        for start, end, beat in source_beats(context.scene_content):
            sensitivities = sorted(set(context.options.sensitivity_hints) | {kind for kind, pattern in _PATTERNS.items() if re.search(pattern, beat, re.I)})
            detected.update(sensitivities)
            found = _issues(context, beat, start, end)
            issues.extend(found)
            if found:
                treatments = [("symbolic", "Static environmental cutaway with no character action or outcome depicted. Hold the unresolved narrative moment for continuity review.", "environmental detail")]
            elif "intimacy" in sensitivities:
                # Never infer age/consent or add a new embrace/body detail. The event
                # remains verbatim in narrative_beat; no sexual act is visualized.
                treatments = [
                    ("cutaway", "Frame a neutral environmental detail away from the intimate event. Keep all bodily interaction off-screen; show no nudity or sexual activity.", "environmental close-up"),
                    ("implied", "Use a quiet transition between moments. Keep the intimate event out of view; no physical act or additional relationship is depicted.", "transition framing"),
                ]
            elif sensitivities:
                if context.profile.audience == "child":
                    treatments = [
                        ("offscreen", "Keep the sensitive event entirely outside the frame. Hold a calm environmental view without disturbing detail, injury, substances or bodily action.", "wide environmental view"),
                        ("reaction", "Use a gentle, restrained response without showing the event or specifying any new action, injury or outcome.", "restrained reaction framing"),
                    ]
                elif context.profile.audience == "teen" or context.profile.maturity_rating in {"general", "mild"}:
                    treatments = [
                        ("reaction", "Use restrained reaction framing with the event outside the frame. Show no wounds, graphic detail, intimate act or substance consumption.", "reaction close-up"),
                        ("implied", "Imply the event through an off-screen transition. No visible impact, injury or bodily detail; introduce no new outcome.", "off-screen transition"),
                        ("aftermath", "Hold a quiet post-event composition without visible injury, bodies, substances or invented consequences. Leave character movement unspecified.", "static closing composition"),
                    ]
                else:
                    treatments = [
                        ("silhouette", "Use a distant abstract silhouette with the sensitive action concealed. Show no bodily contact, wound detail, nudity or substance consumption.", "distant obscured framing"),
                        ("cutaway", "Cut away from the event to an existing environmental detail. Do not depict impact or invent consequences.", "environmental detail"),
                        ("aftermath", "Convey a restrained pause after the event, keeping bodily detail and movement unspecified. Do not add a death, recovery or other unestablished outcome.", "static aftermath framing"),
                    ]
            else:
                treatments = [("direct", "Depict only this established narrative beat: " + beat + " Preserve known capabilities and identities; do not add actions or outcomes.", "contextual medium view")]
            for strategy, instruction, framing in treatments:
                shots.append(AdaptedShot(sequence=len(shots) + 1, narrative_beat=beat, source_start=start, source_end=end,
                    visual_instruction=instruction, framing_hint=framing,
                    character_ids=[row["id"] for row in context.characters], place_ids=[row["id"] for row in context.places],
                    references=context.references, sensitivities=sensitivities, depiction_strategy=strategy,
                    rationale="Continuity issue requires review." if found else
                        f"{context.profile.audience}/{context.profile.maturity_rating}: preserve the event internally while using {strategy} depiction."))
        notes = ["Original beats are audit provenance, not provider prompts. Depiction does not change Story truth or Canon.",
                 "Deterministic sensitivity/capability heuristics are limited to explicit English patterns; review unfamiliar or ambiguous material."]
        if context.options.additional_visual_instruction:
            notes.append("Additional visual instructions are retained in the context digest; deterministic planning does not forward or interpret free-form instructions.")
        return MediaAdaptationPlan(story_id=context.story_id, scene_id=context.scene_id, audience=context.profile.audience,
            maturity_rating=context.profile.maturity_rating, output_format=context.options.output_format,
            sensitivities=sorted(detected), shots=shots, issues=issues, notes=notes, context_digest=context.digest)


def get_shot_planner() -> ShotPlanner:
    return DeterministicShotPlanner()
