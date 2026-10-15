from app.authority.port import (
    AuthorityContext,
    AuthorityResult,
)


class LocalAuthorityEvaluator:
    def evaluate(
        self,
        *,
        action_type: str,
        request: str,
        context: AuthorityContext,
    ) -> AuthorityResult:
        if not self._is_supported_action(action_type):
            return self._block_unsupported_action(
                action_type
            )

        if self._requests_canon_override(request):
            return self._require_approval()

        return self._allow()


    def _is_supported_action(
        self,
        action_type: str,
    ) -> bool:
        return action_type in {
            "scene.generate",
            "story.continue",
            "canon.propose",
        }


    def _requests_canon_override(
        self,
        request: str,
    ) -> bool:
        normalized = request.lower()

        indicators = (
            "change established canon",
            "ignore canon",
            "override canon",
            "contradict canon",
        )

        return any(
            indicator in normalized
            for indicator in indicators
        )


    def _allow(
        self,
    ) -> AuthorityResult:
        return AuthorityResult(
            outcome="ALLOW",
            reason=(
                "Action is within the supported "
                "Sandcastle story scope."
            ),
            confidence=1.0,
        )


    def _require_approval(
        self,
    ) -> AuthorityResult:
        return AuthorityResult(
            outcome="APPROVAL",
            reason=(
                "The requested action explicitly "
                "attempts to alter established canon."
            ),
            confidence=1.0,
        )


    def _block_unsupported_action(
        self,
        action_type: str,
    ) -> AuthorityResult:
        return AuthorityResult(
            outcome="BLOCK",
            reason=(
                f"Unsupported action type: "
                f"{action_type}"
            ),
            confidence=1.0,
        )