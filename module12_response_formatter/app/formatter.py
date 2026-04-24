from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.models import CitationOut, FormatRequest, FormattedResponse


class ResponseFormatterError(Exception):
    """Raised when formatting fails."""


class ResponseFormatterService:
    def __init__(self) -> None:
        self.disclaimer = settings.default_disclaimer
        self.tier_limits = {
            "free": settings.free_tier_word_limit,
            "paid": settings.paid_tier_word_limit,
            "pro": settings.pro_tier_word_limit,
            "enterprise": settings.enterprise_tier_word_limit,
        }
        self.degradation_messages = {
            "citation_fail": (
                "I could not confidently verify enough source citations to provide "
                "a reliable answer. Please review the source materials directly."
            ),
            "hallucination_block": (
                "I could not produce a sufficiently reliable answer based on the "
                "available sources. Please review the cited materials directly "
                "or refine the query."
            ),
            "generic_failure": (
                "I could not prepare a reliable formatted response at this time."
            ),
        }

    def format(self, payload: FormatRequest) -> Tuple[FormattedResponse, Dict[str, Any]]:
        if payload.signal in ("citation_fail", "hallucination_block"):
            response = self._build_degraded_response(
                signal=payload.signal,
                trace_id=payload.trace_id,
                user_tier=payload.user_tier,
            )
            cache_payload = self._build_cache_payload(
                response=response.model_dump(),
                classification_metadata=payload.classification_metadata.model_dump(),
            )
            return response, cache_payload

        if not payload.guardrail_passed_answer:
            raise ResponseFormatterError(
                "guardrail_passed_answer is required when no degradation signal is present"
            )

        cleaned_answer = self.strip_internal_markers(payload.guardrail_passed_answer)
        cited_indices = self.extract_citation_indices(cleaned_answer)

        citations = self.build_citations(
            cited_indices=cited_indices,
            source_chunk_metadata=payload.source_chunk_metadata,
        )

        rendered_answer = self.render_inline_citations(cleaned_answer)
        final_answer = self.apply_verbosity(rendered_answer, payload.user_tier)

        response = FormattedResponse(
            answer_text=final_answer,
            citations=citations,
            disclaimer=self.disclaimer,
            trace_id=payload.trace_id,
        )

        cache_payload = self._build_cache_payload(
            response=response.model_dump(),
            classification_metadata=payload.classification_metadata.model_dump(),
        )

        return response, cache_payload

    def strip_internal_markers(self, answer_text: str) -> str:
        text = answer_text
        patterns = [
            r"\[\[DEBUG:.*?\]\]",
            r"\[\[INTERNAL:.*?\]\]",
            r"<debug>.*?</debug>",
            r"<internal>.*?</internal>",
            r"\{TRACE_ID:.*?\}",
            r"\{CHUNK_INDEX:.*?\}",
            r"__PIPELINE_[A-Z_]+__",
        ]
        for pattern in patterns:
            text = re.sub(pattern, "", text, flags=re.DOTALL)

        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def extract_citation_indices(self, answer_text: str) -> List[int]:
        matches = re.findall(r"\[(\d+)\]", answer_text)
        seen = set()
        ordered_indices: List[int] = []

        for item in matches:
            idx = int(item)
            if idx not in seen:
                seen.add(idx)
                ordered_indices.append(idx)

        return ordered_indices

    def build_citations(
        self,
        cited_indices: List[int],
        source_chunk_metadata: List[Any],
    ) -> List[CitationOut]:
        citations: List[CitationOut] = []

        for new_index, cited_idx in enumerate(cited_indices, start=1):
            source_pos = cited_idx - 1
            if source_pos < 0 or source_pos >= len(source_chunk_metadata):
                continue

            meta = source_chunk_metadata[source_pos]
            section = meta.section_number if meta.section_number else "N/A"

            citations.append(
                CitationOut(
                    index=new_index,
                    act_name=meta.act_name,
                    section=section,
                    url=meta.source_url,
                    year=meta.year,
                )
            )

        return citations

    def render_inline_citations(self, answer_text: str) -> str:
        text = re.sub(r"\s+\[(\d+)\]", r" [\1]", answer_text)
        text = re.sub(r"\[(\d+)\]\s+", r"[\1] ", text)
        return text.strip()

    def apply_verbosity(self, answer_text: str, user_tier: str) -> str:
        limit = self.tier_limits.get(user_tier, self.tier_limits["free"])

        # 0 means uncapped
        if limit == 0:
            return answer_text

        words = answer_text.split()
        if len(words) <= limit:
            return answer_text

        truncated = " ".join(words[:limit]).rstrip()
        return truncated + " ... See full sources for additional detail."

    def _build_degraded_response(
        self,
        signal: str,
        trace_id: str,
        user_tier: str,
    ) -> FormattedResponse:
        msg = self.degradation_messages.get(
            signal,
            self.degradation_messages["generic_failure"],
        )
        msg = self.apply_verbosity(msg, user_tier)

        return FormattedResponse(
            answer_text=msg,
            citations=[],
            disclaimer=self.disclaimer,
            trace_id=trace_id,
        )

    def _build_cache_payload(
        self,
        response: Dict[str, Any],
        classification_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "cache_value": response,
            "tags": {
                "jurisdiction": classification_metadata.get("jurisdiction", []),
                "act_name": classification_metadata.get("act_name"),
            },
            "write_to": ["L1", "L2"],
        }