from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SceneGenerationContext:
    title: str
    premise: str | None
    objective: str | None
    canon: list[dict]
    previous_scenes: list[str]
    request: str


class StoryGenerator(Protocol):
    async def generate_scene(
        self,
        context: SceneGenerationContext,
    ) -> str:
        ...