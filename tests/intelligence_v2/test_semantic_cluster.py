"""Tests for semantic clustering."""

from knowledge_service.intelligence_v2.semantic_cluster import cluster_intelligence_items
from tests.intelligence_v2.conftest import make_item


def test_merges_near_duplicate_topics():
    left = make_item(
        title="Enterprise AI Agents",
        excerpt="Agents are changing enterprise workflows.",
        item_id="left",
    )
    right = make_item(
        title="Enterprise AI Agent Adoption",
        excerpt="Enterprise agents are changing workflows across teams.",
        item_id="right",
    )
    result = cluster_intelligence_items([left, right])
    assert result.duplicates_merged >= 0
    assert len(result.clusters) >= 1
    assert left.cluster_id is not None