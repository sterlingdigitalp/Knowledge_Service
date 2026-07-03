"""Tests for old vs new comparison harness."""

from knowledge_service.intelligence_v2.evaluation.comparison import ComparisonHarness


def test_comparison_rejects_low_quality_samples(golden_failures):
    harness = ComparisonHarness()
    report = harness.compare_samples(golden_failures)
    assert report.rejected_count >= 3
    assert len(report.entries) == len(golden_failures)