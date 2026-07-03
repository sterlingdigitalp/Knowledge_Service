"""Integration tests for IL2 pipeline."""

import os

from knowledge_service.intelligence_v2.integration import apply_intelligence_layer_v2
from knowledge_service.intelligence_v2.pipeline import IntelligenceV2Pipeline
from tests.intelligence_v2.conftest import make_item


def test_pipeline_disabled_by_default():
    old = os.environ.pop("KNOWLEDGE_IL2_ENABLED", None)
    try:
        items, result = apply_intelligence_layer_v2([])
        assert items == []
        assert not result.enabled
    finally:
        if old is not None:
            os.environ["KNOWLEDGE_IL2_ENABLED"] = old


def test_pipeline_resolves_titles_when_enabled(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_IL2_ENABLED", "1")
    items = [
        make_item(
            title="Visit Mercury",
            excerpt="If you want to learn more, go to mercury.com.",
            item_id="m1",
        )
    ]
    pipeline = IntelligenceV2Pipeline()
    result = pipeline.run(items)
    assert result.titles_resolved >= 1
    assert result.rejected_count >= 1


def test_pipeline_rejects_fragment_cards(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_IL2_ENABLED", "1")
    items = [
        make_item(
            title="Figure Where",
            excerpt="If you want to help me figure out where next that should go in the world.",
            item_id="f1",
        )
    ]
    _enhanced, result = apply_intelligence_layer_v2(items)
    assert result.enabled
    assert result.rejected_count >= 1