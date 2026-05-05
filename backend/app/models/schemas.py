"""Pydantic models for Medical Affairs RWE Evidence Builder API."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RequestStatus(str, Enum):
    draft = "draft"
    landscape = "landscape"
    gaps = "gaps"
    studies = "studies"
    iep = "iep"
    in_review = "in_review"
    approved = "approved"
    rejected = "rejected"


class ReviewDecision(str, Enum):
    approve = "approve"
    reject = "reject"
    comment = "comment"


class ChatRole(str, Enum):
    user = "user"
    assistant = "assistant"


class Citation(BaseModel):
    cite_id: str
    source_type: str  # literature | hta | rwe
    label: str
    detail: str
    url: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)


class LiteratureRow(BaseModel):
    pmid: str
    title: str
    authors: str
    journal: str
    year: str
    therapy_area_id: str
    drug_id: str
    study_type: str
    abstract: str
    url: str
    cite_id: str
    confidence: float


class HtaRow(BaseModel):
    hta_id: str
    agency: str
    title: str
    year: str
    drug_id: str
    therapy_area_id: str
    geography_id: str
    decision_summary: str
    url: str
    cite_id: str
    confidence: float


class RweStudyRow(BaseModel):
    study_id: str
    title: str
    sponsor: str
    year: str
    drug_id: str
    therapy_area_id: str
    geography_id: str
    study_design: str
    outcome_summary: str
    url: str
    cite_id: str
    confidence: float


class LandscapePayload(BaseModel):
    literature: List[LiteratureRow]
    hta_decisions: List[HtaRow]
    rwe_studies: List[RweStudyRow]
    narrative: str
    citations: List[Citation]


class GapCell(BaseModel):
    stakeholder: str
    tpp_attribute: str
    gap_topic: str
    severity: str  # low | medium | high
    mitigations: str
    cite_ids: List[str]
    confidence: float


class GapPayload(BaseModel):
    matrix: List[GapCell]
    narrative: str
    citations: List[Citation]


class StudyRecommendation(BaseModel):
    rank: int
    design_id: str
    name: str
    study_type: str
    duration_months: str
    cost_tier: str
    primary_data_sources: str
    rationale: str
    cite_ids: List[str]
    confidence: float


class StudiesPayload(BaseModel):
    recommendations: List[StudyRecommendation]
    narrative: str
    citations: List[Citation]


class IepSectionBlock(BaseModel):
    heading: str
    paragraphs: List[Dict[str, Any]]  # text, cite_ids[], confidence


class IepPayload(BaseModel):
    sections: List[IepSectionBlock]
    citations: List[Citation]


class CreateRequestBody(BaseModel):
    title: str = Field(..., min_length=3)
    tpp_summary: str = Field(..., min_length=10)
    drug_id: str
    therapy_area_id: str
    geography_id: str
    lifecycle_stage: str
    auto_run_agents: bool = False


class RequestSummary(BaseModel):
    request_id: str
    created_at: str
    updated_at: str
    title: str
    drug_id: str
    therapy_area_id: str
    geography_id: str
    lifecycle_stage: str
    status: str


class RequestDetail(RequestSummary):
    tpp_summary: str
    drug_name: Optional[str] = None
    therapy_area_name: Optional[str] = None
    geography_name: Optional[str] = None
    landscape: Optional[LandscapePayload] = None
    gaps: Optional[GapPayload] = None
    studies: Optional[StudiesPayload] = None
    iep: Optional[IepPayload] = None


class ChatMessage(BaseModel):
    message_id: str
    request_id: str
    role: str
    content: str
    timestamp: str


class ChatBody(BaseModel):
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    assistant_message: ChatMessage
    iep_updated: bool = False


class ReviewBody(BaseModel):
    decision: ReviewDecision
    approver: str = Field(default="Medical Director")
    comments: str = ""


class ReviewRecord(BaseModel):
    review_id: str
    request_id: str
    approver: str
    decision: str
    comments: str
    timestamp: str


class KpiRow(BaseModel):
    kpi_id: str
    name: str
    baseline: str
    target: str
    unit: str


class RegenerateSectionBody(BaseModel):
    section_heading: str
