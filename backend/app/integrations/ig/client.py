"""Inspected IG b369c9d image HTTP contract; live auth is deliberately unavailable."""
import os
from urllib.parse import quote

import httpx
from pydantic import ValidationError

from app.media.execution_client import (
    ExecutionClientError, ExecutionRejected, ExecutionResult, ExecutionUnavailable,
    ExternalStatus, GeneratedImage, Submission,
)
from app.media.schemas import MediaRequest, MediaType

AUTH_BLOCKER = "IG requires browser-session authentication; a service-caller/actor authentication contract is required before live execution."


class IGMediaExecutionClient:
    backend_name = "ig"

    def __init__(self, base_url: str = "", *, transport: httpx.MockTransport | None = None):
        self.base_url = base_url.rstrip("/")
        # Only in-process contract tests may supply transport until safe live auth exists.
        if transport is not None and not isinstance(transport, httpx.MockTransport):
            raise ValueError("Only mock HTTP transport is supported until IG service authentication exists")
        self._transport = transport

    def _http(self, method: str, path: str, **kwargs) -> dict:
        if self._transport is None:
            raise ExecutionUnavailable(AUTH_BLOCKER)
        if not self.base_url.startswith(("https://", "http://")):
            raise ExecutionUnavailable("IG_BASE_URL is not configured")
        try:
            with httpx.Client(base_url=self.base_url, transport=self._transport, timeout=15, follow_redirects=False, trust_env=False) as client:
                response = client.request(method, path, **kwargs)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Invalid response")
            return payload
        except (httpx.HTTPError, ValueError) as error:
            # Never persist raw upstream response bodies, credentials, or provider diagnostics.
            raise ExecutionClientError("IG request failed or returned an invalid response") from error

    def submit(self, request: MediaRequest, *, actor_id: str, correlation_id: str) -> Submission:
        if self._transport is None:
            raise ExecutionUnavailable(AUTH_BLOCKER)
        if request.media_type != MediaType.IMAGE:
            raise ExecutionRejected("Only image execution is supported")
        if request.aspect_ratio not in {None, "2:3", "4:5", "1:1", "16:9"}:
            raise ExecutionRejected("IG does not support this aspect ratio")
        if any(ref.kind in {"generated_artifact", "uploaded_artifact"} for ref in request.references):
            raise ExecutionRejected("Visual artifact references require a verified IG artifact resolver; opaque IDs cannot be assumed to be IG artifact IDs")
        payload = self._http("POST", "/v2/media/generations", json={
            "media_type": "image", "interface_level": "easy", "strategy": "single",
            "intent": {"description": request.prompt},
            "output": {"quality": "standard", "aspect_ratio": request.aspect_ratio,
                       "count": 1, "layout": {"type": "single"}},
            # Story identity is already compiled into prompt text; it is not an image artifact.
            "references": [],
        })
        try:
            # IG currently returns an image request ID, not a Job ID.
            return Submission(external_execution_id=payload["request_id"])
        except (KeyError, ValidationError) as error:
            raise ExecutionClientError("IG returned no valid image request ID") from error

    def _image(self, external_execution_id: str) -> dict:
        payload = self._http("GET", f"/v1/images/{quote(external_execution_id, safe='')}")
        if payload.get("request_id") != external_execution_id:
            raise ExecutionClientError("IG returned an unexpected image request ID")
        return payload

    def get_status(self, external_execution_id: str, *, actor_id: str) -> ExternalStatus:
        payload = self._image(external_execution_id)
        mapping = {"generating": "running", "completed": "completed", "failed": "failed"}
        status = mapping.get(payload.get("status"))
        if status is None:
            raise ExecutionClientError("IG returned an unknown image status")
        return ExternalStatus(status=status, error_message="IG image generation failed" if status == "failed" else None)

    def get_result(self, external_execution_id: str, *, actor_id: str) -> ExecutionResult:
        payload = self._image(external_execution_id)
        if payload.get("status") != "completed":
            raise ExecutionClientError("IG image result is not complete")
        try:
            return ExecutionResult(images=[GeneratedImage(
                external_reference=external_execution_id,
                retrieval_reference=f"{self.base_url}/v1/images/{quote(external_execution_id, safe='')}/content",
                mime_type=payload.get("mime_type"),
                metadata={"size_bytes": payload.get("size_bytes"), "generation_time_ms": payload.get("generation_time_ms")},
            )])
        except ValidationError as error:
            raise ExecutionClientError("IG returned invalid image metadata") from error


def get_execution_client() -> IGMediaExecutionClient:
    # No invented service token, login, cookie forwarding, or eager network activity.
    return IGMediaExecutionClient(os.getenv("IG_BASE_URL", ""))
