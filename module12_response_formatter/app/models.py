from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


UserTier = Literal["free", "paid", "pro", "enterprise"]
SignalType = Optional[Literal["citation_fail", "hallucination_block"]]


class GuardrailReport(BaseModel):
    claims_checked: int = 0
    entailed_count: int = 0
    flagged_count: int = 0
    flagged_claims: List[str] = Field(default_factory=list)


class CitationVerificationReport(BaseModel):
    total_citations: int = 0
    verified_count: int = 0
    removed_count: int = 0
    flagged_markers: List[int] = Field(default_factory=list)


class SourceChunkMetadata(BaseModel):
    source_url: Optional[str] = None
    act_name: str = "Unknown Source"
    section_number: Optional[str] = None
    year: Optional[int] = None


class ClassificationMetadata(BaseModel):
    jurisdiction: List[str] = Field(default_factory=list)
    act_name: Optional[str] = None


class FormatRequest(BaseModel):
    guardrail_passed_answer: Optional[str] = None
    guardrail_report: GuardrailReport
    citation_verification_report: CitationVerificationReport
    source_chunk_metadata: List[SourceChunkMetadata] = Field(default_factory=list)
    user_tier: UserTier = "free"
    trace_id: str
    classification_metadata: ClassificationMetadata = Field(
        default_factory=ClassificationMetadata
    )
    signal: SignalType = None


class CitationOut(BaseModel):
    index: int
    act_name: str
    section: str
    url: Optional[str] = None
    year: Optional[int] = None


class FormattedResponse(BaseModel):
    answer_text: str
    citations: List[CitationOut]
    disclaimer: str
    trace_id: str


class CachePayload(BaseModel):
    cache_value: Dict[str, Any]
    tags: Dict[str, Any]
    write_to: List[str]


class FormatAPIResponse(BaseModel):
    formatted_response: FormattedResponse
    cache_payload: CachePayload
    cache_write_status: str