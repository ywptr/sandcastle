import os

from openai import AsyncOpenAI

from app.stories.generator import (
    SceneGenerationContext,
)


class OpenAIStoryGenerator:
    def __init__(self) -> None:
        self.client = AsyncOpenAI()

        self.model = os.environ["SANDCASTLE_TEXT_MODEL"]

    async def generate_scene(
        self,
        context: SceneGenerationContext,
    ) -> str:
        response = await self.client.responses.create(
            model=self.model,
            input=build_prompt(context),
        )

        return response.output_text.strip()


def build_prompt(
    context: SceneGenerationContext,
) -> str:
    return f"""
You are the story-writing engine inside Sandcastle story-building app.

Write the next scene.

STORY TITLE
{context.title}

PREMISE
{context.premise or "Not specified"}

OBJECTIVE
{context.objective or "Not specified"}

ESTABLISHED CANON
{format_canon(context.canon)}

PREVIOUS SCENES
{format_previous_scenes(context.previous_scenes)}

USER REQUEST
{context.request}

Requirements:
- Preserve established canon.
- Continue naturally from earlier scenes.
- Do not contradict known facts.
- Return only scene prose.
""".strip()


def format_canon(
    canon: list[dict],
) -> str:
    if not canon:
        return "No canon established yet."

    return "\n".join(
        f"- [{entry['type']}] "
        f"{entry['key']}: "
        f"{entry['value']}"
        for entry in canon
    )


def format_previous_scenes(
    scenes: list[str],
) -> str:
    if not scenes:
        return "This is the first scene."

    return "\n\n".join(
        f"Scene {index + 1}:\n{content}"
        for index, content
        in enumerate(scenes)
    )