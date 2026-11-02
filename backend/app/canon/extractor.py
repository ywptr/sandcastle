from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ExtractedCanonFact:
    type: str
    key: str
    value: str


class CanonExtractor(Protocol):
    async def extract(
        self,
        *,
        story_title: str,
        scene_content: str,
    ) -> list[ExtractedCanonFact]:
        ...