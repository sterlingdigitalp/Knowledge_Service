"""LLM provider abstraction for analyst-quality generation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ThemeNamingRequest:
    keywords: List[str]
    entities: List[str]
    sample_claims: List[str]
    sources: List[str]
    speakers: List[str]


@dataclass
class SummaryRequest:
    theme_label: str
    title: str
    keywords: List[str]
    entities: List[str]
    sources: List[str]
    speakers: List[str]
    claim_excerpts: List[str]
    novelty_classification: str
    importance_band: str
    corroboration_count: int
    contradictions: int
    theme_evolution: str = ""


@dataclass
class ConversationRequest:
    intelligence_item_id: str
    title: str
    executive_summary: str
    user_message: str
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    previous_response_id: Optional[str] = None


@dataclass
class ConversationResult:
    text: str
    response_id: Optional[str] = None
    provider: str = ""
    used_fallback: bool = False


@dataclass
class BriefPolishRequest:
    title: str
    what_changed: str
    why_you_care: str
    evidence_summary: str


@dataclass
class BriefItemEnhancementRequest:
    theme_label: str
    title: str
    executive_summary: str
    why_it_matters: str
    keywords: List[str]
    entities: List[str]
    sources: List[str]
    speakers: List[str]
    claim_excerpts: List[str]
    novelty_classification: str
    importance_band: str
    corroboration_count: int
    contradictions: int
    theme_evolution: str = ""


@dataclass
class BriefItemEnhancementResult:
    title: str
    executive_summary: str
    why_it_matters: str
    provider: str = ""
    from_cache: bool = False


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    def name_theme(self, request: ThemeNamingRequest) -> str:
        raise NotImplementedError

    @abstractmethod
    def executive_summary(self, request: SummaryRequest) -> str:
        raise NotImplementedError

    @abstractmethod
    def converse(self, request: ConversationRequest) -> ConversationResult:
        raise NotImplementedError

    def suggested_followups(
        self,
        *,
        title: str,
        executive_summary: str,
        contradiction_count: int = 0,
        corroboration_count: int = 0,
    ) -> List[str]:
        prompts = [
            "What should I watch next?",
            "Show me the timeline",
            "What evidence supports this?",
            "Are there competing viewpoints?",
        ]
        if contradiction_count:
            prompts.insert(0, "Explain the contradictions")
        if corroboration_count:
            prompts.insert(1, "Who corroborated this independently?")
        return prompts[:5]

    def polish_brief_entry(self, request: BriefPolishRequest) -> str:
        return request.what_changed

    def enhance_brief_item(self, request: BriefItemEnhancementRequest) -> BriefItemEnhancementResult:
        """Single-item editor pass: title, summary, and why-it-matters."""
        naming = ThemeNamingRequest(
            keywords=request.keywords,
            entities=request.entities,
            sample_claims=request.claim_excerpts,
            sources=request.sources,
            speakers=request.speakers,
        )
        title = self.name_theme(naming)
        summary = self.executive_summary(SummaryRequest(
            theme_label=request.theme_label,
            title=title,
            keywords=request.keywords,
            entities=request.entities,
            sources=request.sources,
            speakers=request.speakers,
            claim_excerpts=request.claim_excerpts,
            novelty_classification=request.novelty_classification,
            importance_band=request.importance_band,
            corroboration_count=request.corroboration_count,
            contradictions=request.contradictions,
            theme_evolution=request.theme_evolution,
        ))
        return BriefItemEnhancementResult(
            title=title,
            executive_summary=summary,
            why_it_matters=request.why_it_matters,
            provider=self.name,
        )

    def runtime_metrics(self) -> Dict[str, Any]:
        return {"provider": self.name, "status": "ready"}