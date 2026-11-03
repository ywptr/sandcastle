"""Execution contract independent of transport, provider, and infrastructure."""
from typing import Literal, Protocol

from pydantic import Field, field_validator

from app.media.schemas import MediaRequest
from app.validation import InputModel, Name, NonBlank

ExecutionState = Literal["pending", "submitted", "running", "completed", "failed"]


class ExecutionClientError(Exception):
    """Safe, credential-free error suitable for persisted execution diagnostics."""


class ExecutionUnavailable(ExecutionClientError):
    pass


class ExecutionRejected(ExecutionClientError):
    pass


class Submission(InputModel):
    external_execution_id: Name


class ExternalStatus(InputModel):
    status: ExecutionState
    error_message: NonBlank | None = None


class GeneratedImage(InputModel):
    external_reference: Name
    retrieval_reference: NonBlank
    external_artifact_id: Name | None = None
    mime_type: Name | None = None
    metadata: dict[str, str | int | None] = Field(default_factory=dict)

    @field_validator("retrieval_reference")
    @classmethod
    def external_reference_only(cls, value: str) -> str:
        if value.lower().startswith(("data:", "file:", "javascript:")):
            raise ValueError("Results must reference external media, not inline bytes or local files")
        return value


class ExecutionResult(InputModel):
    images: list[GeneratedImage] = Field(min_length=1)


class MediaExecutionClient(Protocol):
    backend_name: str

    def submit(self, request: MediaRequest, *, actor_id: str, correlation_id: str) -> Submission:
        """Actor is the requesting user; caller credentials belong to the adapter."""
        ...

    def get_status(self, external_execution_id: str, *, actor_id: str) -> ExternalStatus:
        ...

    def get_result(self, external_execution_id: str, *, actor_id: str) -> ExecutionResult:
        ...
