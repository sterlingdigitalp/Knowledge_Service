"""Agent H — Runtime 3 integration hooks."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..analyst.synthesis.models import IntelligenceItem
from .brief import Runtime3Brief, Runtime3BriefGenerator
from .config import Runtime3Config, is_runtime3_enabled
from .models import Runtime3Result
from .pipeline import Runtime3Pipeline, stories_to_intelligence_items


class Runtime3Layer:
    """Optional semantic understanding layer — does not replace Runtime 1 or IL2."""

    def __init__(self, config: Runtime3Config | None = None, state_dir: str | None = None):
        self.config = config or Runtime3Config.from_env()
        self.state_dir = state_dir
        self.pipeline = Runtime3Pipeline(self.config, state_dir=state_dir)
        self.brief_generator = Runtime3BriefGenerator()

    @property
    def enabled(self) -> bool:
        return is_runtime3_enabled()

    def run(
        self,
        *,
        episode_ids: Optional[List[str]] = None,
        date: Optional[str] = None,
    ) -> Tuple[Runtime3Result, Optional[Runtime3Brief]]:
        if not self.enabled:
            return Runtime3Result(enabled=False), None
        if date:
            result = self.pipeline.run_for_archive_date(date, state_dir=self.state_dir)
            brief = self.brief_generator.generate(result, date=date)
            return result, brief
        result = self.pipeline.run(state_dir=self.state_dir, episode_ids=episode_ids)
        brief = self.brief_generator.generate(result, date=date or "")
        return result, brief

    def to_intelligence_items(self, result: Runtime3Result) -> List[IntelligenceItem]:
        """Bridge Story Objects to IntelligenceItem for downstream compatibility."""
        return stories_to_intelligence_items(result.stories)


def apply_runtime3_layer(
    *,
    state_dir: str | None = None,
    episode_ids: Optional[List[str]] = None,
    date: Optional[str] = None,
    config: Runtime3Config | None = None,
) -> Tuple[Runtime3Result, Optional[Runtime3Brief], List[IntelligenceItem]]:
    """Run Runtime 3 when KNOWLEDGE_RUNTIME3_ENABLED=1; empty otherwise."""
    layer = Runtime3Layer(config, state_dir=state_dir)
    if not layer.enabled:
        return Runtime3Result(enabled=False), None, []
    result, brief = layer.run(episode_ids=episode_ids, date=date)
    items = layer.to_intelligence_items(result)
    return result, brief, items