"""Tests for evaluation corpus builder."""

from pathlib import Path

from knowledge_service.intelligence_v2.evaluation.corpus_builder import EvaluationCorpusBuilder


def test_builds_corpus_from_latest_brief(tmp_path):
    repo = Path(__file__).resolve().parents[2]
    builder = EvaluationCorpusBuilder(repo)
    manifest = builder.build(tmp_path / "corpus")
    assert manifest.sample_count >= 1
    assert (tmp_path / "corpus" / "manifest.json").exists()
    assert "knowledge_service_frontend" in manifest.sources