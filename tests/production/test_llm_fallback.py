import httpx

from knowledge_service.production.llm.accounting import get_llm_accounting, reset_llm_accounting
from knowledge_service.production.llm.provider import SummaryRequest
from knowledge_service.production.llm.xai_responses import XAIResponsesProvider


def test_malformed_response_falls_back_to_heuristic(monkeypatch):
    reset_llm_accounting()

    def fake_post(url, **kwargs):
        request = httpx.Request("POST", url)
        return httpx.Response(200, request=request, json={"id": "x", "status": "completed", "output": []})

    monkeypatch.setenv("XAI_API_KEY", "test-key")
    monkeypatch.setattr(httpx, "post", fake_post)

    provider = XAIResponsesProvider()
    summary = provider.executive_summary(SummaryRequest(
        theme_label="inference",
        title="Inference Economics",
        keywords=["inference"],
        entities=["NVIDIA"],
        sources=["Podcast A"],
        speakers=["Speaker A"],
        claim_excerpts=["Inference costs are rising."],
        novelty_classification="new",
        importance_band="high",
        corroboration_count=2,
        contradictions=0,
    ))

    assert "independent sources" in summary.lower() or "why it matters" in summary.lower()
    accounting = get_llm_accounting().summary()
    assert accounting["failures"] >= 1 or accounting["fallback_events"] >= 0


def test_missing_api_key_uses_fallback_without_network(monkeypatch):
    reset_llm_accounting()
    monkeypatch.delenv("XAI_API_KEY", raising=False)

    provider = XAIResponsesProvider(api_key=None)
    summary = provider.executive_summary(SummaryRequest(
        theme_label="agents",
        title="Enterprise AI Agents",
        keywords=["agent"],
        entities=["OpenAI"],
        sources=["Roundtable"],
        speakers=["Operator"],
        claim_excerpts=["Teams are shipping autonomous agents."],
        novelty_classification="update",
        importance_band="medium",
        corroboration_count=1,
        contradictions=0,
    ))

    assert summary
    assert get_llm_accounting().summary()["fallback_events"] >= 1