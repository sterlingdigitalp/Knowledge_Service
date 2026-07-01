"""Production Intelligence Pipeline — Phase 5 end-to-end."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ..analyst.pipeline import IntelligenceAnalystPipeline, PipelineResult
from ..intelligence.models import now_iso
from .benchmark import PhaseBenchmark
from .conversation.deep_dive_v3 import DeepDiveConversationEngine
from .enhancement import ProductionEnhancementLayer, ProductionResult
from .personalization.feedback import UserFeedbackEngine
from .personalization.store import PersonalizationStore
from .scheduler.brief_scheduler import MorningBriefScheduler
from .store import ProductionStore


@dataclass
class ProductionPipelineResult:
    analyst: PipelineResult
    production: ProductionResult
    benchmark: Dict[str, Any] = field(default_factory=dict)
    latency_seconds: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analyst": self.analyst.to_dict(),
            "production": self.production.to_dict(),
            "benchmark": dict(self.benchmark),
            "latency_seconds": dict(self.latency_seconds),
        }


class ProductionIntelligencePipeline:
    """Run acquisition-complete analyst pipeline plus Phase 5 enhancements."""

    def __init__(self, state_dir: str):
        self.state_dir = state_dir
        self.analyst = IntelligenceAnalystPipeline(state_dir)
        self.enhancement = ProductionEnhancementLayer(state_dir)
        self.personalization = PersonalizationStore(self.analyst.state)
        self.feedback = UserFeedbackEngine(self.personalization)
        self.conversation = DeepDiveConversationEngine(self.personalization)
        self.scheduler = MorningBriefScheduler(self.analyst.state)
        self.production_store = ProductionStore(self.analyst.state)
        self.benchmark = PhaseBenchmark()

    def run(self, *, manual: bool = True) -> ProductionPipelineResult:
        started = time.perf_counter()
        analyst_result = self.analyst.run()
        production_result = self.enhancement.enhance(analyst_result)

        claim_texts = [claim.claim_text for claim in self.analyst.store.load_claims()]
        benchmark = self.benchmark.from_claim_texts(claim_texts)
        benchmark["brief"] = self.benchmark.compare_briefs(
            analyst_result.intelligence_brief.to_dict() if analyst_result.intelligence_brief else None,
            production_result.intelligence_brief_v3.to_dict() if production_result.intelligence_brief_v3 else None,
        )
        self.production_store.save_benchmark(benchmark)

        if manual or self.scheduler.should_run():
            self.scheduler.record_run(analyst_result.run_id, manual=manual)

        elapsed = round(time.perf_counter() - started, 3)
        return ProductionPipelineResult(
            analyst=analyst_result,
            production=production_result,
            benchmark=benchmark,
            latency_seconds={
                "analyst": analyst_result.latency_seconds.get("total", 0.0),
                "production": production_result.latency_seconds.get("total", 0.0),
                "total": elapsed,
            },
        )

    def record_tell_me_more(self, intelligence_item_id: str, *, duration_seconds: float = 0.0) -> Dict[str, Any]:
        event = self.feedback.tell_me_more(intelligence_item_id, duration_seconds=duration_seconds)
        items = self.enhancement.synthesis_store.load_items()
        self.enhancement.ranking.learn_from_feedback(items)
        return event

    def start_conversation(self, intelligence_item_id: str) -> Optional[Dict[str, Any]]:
        item = next((row for row in self.enhancement.synthesis_store.load_items() if row.item_id == intelligence_item_id), None)
        if item is None:
            return None
        session = self.conversation.start(item)
        self.feedback.tell_me_more(intelligence_item_id)
        return session

    def continue_conversation(self, session_id: str, user_message: str) -> Optional[Dict[str, Any]]:
        sessions = self.personalization.load_sessions().get("sessions", {})
        session = sessions.get(session_id)
        if session is None:
            return None
        item = next(
            (row for row in self.enhancement.synthesis_store.load_items() if row.item_id == session.get("intelligence_item_id")),
            None,
        )
        if item is None:
            return None
        return self.conversation.continue_conversation(session_id, user_message, item)

    def rerun_with_learning(self) -> ProductionPipelineResult:
        """Demonstrate ranking adaptation after feedback."""
        return self.run(manual=True)

    @classmethod
    def run_on_state(cls, state_dir: str) -> ProductionPipelineResult:
        return cls(state_dir).run()