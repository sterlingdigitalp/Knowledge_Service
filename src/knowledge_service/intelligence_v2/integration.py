"""Integration hooks for Knowledge_Service production layer."""

from __future__ import annotations

from copy import deepcopy
from typing import List, Sequence, Tuple

from ..analyst.synthesis.models import IntelligenceItem
from .config import IL2Config, is_il2_enabled
from .models import IL2Result
from .pipeline import IntelligenceV2Pipeline


class IntelligenceLayerV2:
    """Optional post-synthesis enhancement — does not replace Runtime 1."""

    def __init__(self, config: IL2Config | None = None):
        self.config = config or IL2Config.from_env()
        self.pipeline = IntelligenceV2Pipeline(self.config)

    @property
    def enabled(self) -> bool:
        return is_il2_enabled()

    def enhance(self, items: Sequence[IntelligenceItem]) -> Tuple[List[IntelligenceItem], IL2Result]:
        if not self.enabled:
            return list(items), IL2Result(enabled=False)
        working = deepcopy(list(items))
        result = self.pipeline.run(working)
        filtered = self.pipeline.filter_items(working, result)
        return filtered, result


def apply_intelligence_layer_v2(
    items: Sequence[IntelligenceItem],
    *,
    config: IL2Config | None = None,
) -> Tuple[List[IntelligenceItem], IL2Result]:
    """Apply IL2 when KNOWLEDGE_IL2_ENABLED=1; passthrough otherwise."""
    layer = IntelligenceLayerV2(config)
    return layer.enhance(items)