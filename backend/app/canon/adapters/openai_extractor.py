import json

from openai import AsyncOpenAI

from app.canon.extractor import (
    CanonExtractor,
    ExtractedCanonFact,
)


class OpenAICanonExtractor(CanonExtractor):
    def __init__(self, *, api_key: str, model: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key, base_url="https://api.openai.com/v1", timeout=60.0, max_retries=0)
        self.model = model


    async def extract(
        self,
        *,
        story_title: str,
        scene_content: str,
    ) -> list[ExtractedCanonFact]:
        response = await self.client.responses.create(
            model=self.model,
            input=build_prompt(
                story_title,
                scene_content,
            ),
        )

        payload = json.loads(
            response.output_text
        )

        return [
            ExtractedCanonFact(
                type=item["type"],
                key=item["key"],
                value=item["value"],
                evidence=item["evidence"],
                subject_name=item.get("subject_name"),
                subject_id=item.get("subject_id"),
                fact_type=item.get("fact_type", "statement"),
                explicit=item.get("explicit", True),
            )
            for item in payload
        ]


def build_prompt(
    story_title: str,
    scene_content: str,
) -> str:
    return f"""
Extract durable story facts from this scene.

Story:
{story_title}

Scene:
{scene_content}

Return JSON only.

Format:
[
  {{
    "type": "character",
    "key": "eye_color",
    "value": "green",
    "subject_name": "Mara",
    "fact_type": "physical_trait",
    "evidence": "Mara has green eyes."
  }}
]

Use type character, place, world, timeline, event, or story.
Use a short property key such as eye_color rather than a name-based path.
Include the exact source excerpt as evidence. Mark inferred or ambiguous facts
with explicit=false. Return subject_name for named Characters or Places;
do not invent subject IDs or create new domain objects.

Only extract facts that may matter for future continuity.
Do not extract temporary prose details unless they establish
something that should remain consistent.
""".strip()