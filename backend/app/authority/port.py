from dataclasses import dataclass
from typing import Protocol


@dataclass
class AuthorityContext:
    story_id: str
    objective: str | None
    canon_entries: list[dict]


@dataclass
class AuthorityResult:
    outcome: str
    reason: str
    confidence: float | None = None


class AuthorityEvaluator(Protocol):
    def evaluate(
        self,
        *,
        action_type: str,
        request: str,
        context: AuthorityContext,
    ) -> AuthorityResult:
        ...