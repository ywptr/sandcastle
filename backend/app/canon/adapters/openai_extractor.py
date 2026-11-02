import json
import os

from openai import AsyncOpenAI

from app.canon.extractor import (
    CanonExtractor,
    ExtractedCanonFact,
)


class OpenAICanonExtractor(CanonExtractor):
    def __init__(self) -> None:
        self.client = AsyncOpenAI()
        self.model = os.environ[
            "SANDCASTLE_TEXT_MODEL"
        ]


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
    "key": "character.mara.eye_color",
    "value": "Mara has green eyes."
  }}
]

Useful types include:
character
outfit
world
timeline
relationship
rule
plot
location
object
food
vehicle
organization

Only extract facts that may matter for future continuity.
Do not extract temporary prose details unless they establish
something that should remain consistent.
""".strip()