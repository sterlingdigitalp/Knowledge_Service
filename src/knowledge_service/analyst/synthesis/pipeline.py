"""Intelligence Synthesis Pipeline — themes → items → brief."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ...intelligence.models import now_iso, stable_id
from ...intelligence.state import FileStateStore
from ..models import CorroborationCluster, ScoredClaim
from .briefing.deep_dive_v2 import IntelligenceDeepDiveGenerator
from .briefing.morning_brief_v2 import IntelligenceBriefGenerator
from .items.engine import IntelligenceItemEngine
from .models import IntelligenceBrief, IntelligenceDeepDive, IntelligenceItem, ThemeEvolution
from .store import SynthesisStore
from .themes.discovery import ThemeDiscoveryEngine
from .themes.evolution import ThemeEvolutionEngine


@dataclass
class SynthesisResult:
    run_id: str
    themes_discovered: int = 0
    intelligence_items: int = 0
    brief: Optional[IntelligenceBrief] = None
    compression_ratio: float = 0.0
    claims_synthesized: int = 0
    theme_evolutions: List[ThemeEvolution] = field(default_factory=list)
    latency_seconds: Dict[str, float] = field(default_factory=dict)
    status: str = "completed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "themes_discovered": self.themes_discovered,
            "intelligence_items": self.intelligence_items,
            "brief": self.brief.to_dict() if self.brief else None,
            "compression_ratio": self.compression_ratio,
            "claims_synthesized": self.claims_synthesized,
            "theme_evolutions": [record.to_dict() for record in self.theme_evolutions],
            "latency_seconds": dict(self.latency_seconds),
            "status": self.status,
        }


class IntelligenceSynthesisPipeline:
    """Phase 4.1 synthesis layer on top of scored claims."""

    def __init__(self, state_dir: str):
        self.state = FileStateStore(state_dir)
        self.store = SynthesisStore(self.state)
        self.theme_discovery = ThemeDiscoveryEngine()
        self.theme_evolution = ThemeEvolutionEngine()
        self.item_engine = IntelligenceItemEngine()
        self.brief_generator = IntelligenceBriefGenerator()
        self.deep_dive_generator = IntelligenceDeepDiveGenerator()

    def run(
        self,
        scored_claims: List[ScoredClaim],
        clusters: List[CorroborationCluster],
        pipeline_run_id: str = "",
    ) -> SynthesisResult:
        started = time.perf_counter()
        run_id = stable_id("synthesis-run", now_iso())
        result = SynthesisResult(run_id=run_id, claims_synthesized=len(scored_claims))

        theme_started = time.perf_counter()
        themes = self.theme_discovery.discover(scored_claims)
        historical_themes = self.store.load_themes()
        evolutions = self.theme_evolution.evaluate(themes, historical_themes)
        merged_history = self.theme_evolution.merge_history(themes, historical_themes)
        self.store.save_themes(merged_history)
        self.store.append_theme_history(evolutions)
        result.latency_seconds["theme_discovery"] = round(time.perf_counter() - theme_started, 3)
        result.themes_discovered = len(themes)
        result.theme_evolutions = evolutions

        item_started = time.perf_counter()
        items = self.item_engine.synthesize(scored_claims, themes, clusters, evolutions)
        self.store.save_items(items)
        result.latency_seconds["item_synthesis"] = round(time.perf_counter() - item_started, 3)
        result.intelligence_items = len(items)

        brief_started = time.perf_counter()
        brief = self.brief_generator.generate(items, pipeline_run_id=pipeline_run_id, claims_synthesized=len(scored_claims))
        self.store.save_brief(brief)
        result.brief = brief
        result.compression_ratio = brief.compression_ratio
        result.latency_seconds["brief_generation"] = round(time.perf_counter() - brief_started, 3)
        result.latency_seconds["total"] = round(time.perf_counter() - started, 3)

        self.store.record_run({
            "run_id": run_id,
            "started_at": now_iso(),
            "result": result.to_dict(),
        })
        return result

    def deep_dive(
        self,
        intelligence_item_id: str,
        scored_claims: List[ScoredClaim],
        all_claims,
    ) -> Optional[IntelligenceDeepDive]:
        items = self.store.load_items()
        return self.deep_dive_generator.generate(intelligence_item_id, items, scored_claims, all_claims)