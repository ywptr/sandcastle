from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.canon.extractor import ExtractedCanonFact
from app.validation import InputModel, Name

CandidateStatus = Literal["pending", "approved", "rejected"]
ContinuityClassification = Literal["new", "consistent", "conflict", "uncertain"]


class ManualCandidate(ExtractedCanonFact):
    scene_id: Name | None = None


class CandidateApproval(InputModel):
    replace_conflicts: bool = False
    accept_uncertain: bool = False
    subject_id: Name | None = None
    note: str | None = None


class CandidateRejection(InputModel):
    note: str | None = None


class CanonCandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    canon_candidate_id: str
    user_id: str
    story_id: str
    scene_id: str | None
    type: str
    subject_id: str | None
    subject_name: str | None
    fact_type: str
    key: str
    value: str
    evidence: str
    source_kind: str
    source_snapshot: str
    source_hash: str
    status: CandidateStatus
    classification: ContinuityClassification
    confidence: float | None
    reasoning: str
    comparison_snapshot: list[dict]
    superseded_entry_ids: list[str]
    approved_canon_entry_id: str | None
    created_at: datetime
    analyzed_at: datetime
    reviewed_at: datetime | None
    review_note: str | None


class ContinuityIssue(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    canon_candidate_id: str
    scene_id: str | None
    type: str
    subject_id: str | None
    key: str
    value: str
    classification: ContinuityClassification
    reasoning: str


class ContinuityReport(BaseModel):
    story_id: str
    scene_id: str | None
    status: Literal["pending"] = "pending"
    counts: dict[ContinuityClassification, int]
    total: int
    issues: list[ContinuityIssue] = Field(default_factory=list)
