from dataclasses import dataclass, field
from typing import Protocol
from app.media.production.schemas import ContinuityContext, ProductionProposal, TargetFormat
from app.stories.scene_schemas import SceneResponse


@dataclass(frozen=True)
class NarrativeMediaContext:
    story_id: str
    scene: SceneResponse
    continuity: ContinuityContext
    target_format: TargetFormat
    workflow: dict
    source_digest: str
    context_digest: str
    instruction: str | None = None
    output_language: str | None = None
    # Future typed Creative Direction can be added here without changing adapters.
    creative_direction: dict = field(default_factory=dict)

    def narrative_data(self):
        from app.languages.service import production_language
        return {"language_context": production_language(self.continuity.story.language, self.output_language), "allowed_ids": {
                    "character_ids": [c.character_id for c in self.continuity.characters],
                    "place_ids": [p.place_id for p in self.continuity.places],
                    "artifact_ids": [r.reference_id for r in self.continuity.references
                        if r.kind in {"artifact", "generated_artifact", "uploaded_artifact"}],
                }, "story_id": self.story_id, "scene": self.scene.model_dump(mode="json"),
                "continuity": self.continuity.model_dump(mode="json"), "target_format": self.target_format,
                "workflow": self.workflow, "instruction": self.instruction, "creative_direction": self.creative_direction}


class NarrativeMediaTranslator(Protocol):
    async def translate(self, context: NarrativeMediaContext) -> ProductionProposal: ...
