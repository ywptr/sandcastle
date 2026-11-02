from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class SceneGenerationContext:
    title: str
    premise: str | None
    objective: str | None
    canon: list[dict]
    previous_scenes: list[str]
    request: str
    characters: list[dict] = field(default_factory=list)
    places: list[dict] = field(default_factory=list)


class StoryGenerator(Protocol):
    async def generate_scene(
        self,
        context: SceneGenerationContext,
    ) -> str:
        ...