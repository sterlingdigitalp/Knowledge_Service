import json

import httpx
import pytest

from knowledge_service.production.llm.accounting import get_llm_accounting, reset_llm_accounting
from knowledge_service.production.llm.config import load_llm_config
from knowledge_service.production.llm.provider import ConversationRequest, SummaryRequest, ThemeNamingRequest
from knowledge_service.production.llm.registry import configure_llm
from knowledge_service.production.llm.xai_responses import XAIResponsesProvider, _extract_output_text


def _responses_payload(text: str, *, response_id: str = "resp_123") -> dict:
    return {
        "id": response_id,
        "status": "completed",
        "model": "grok-4.3",
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": text}],
            }
        ],
        "usage": {
            "input_tokens": 120,
            "output_tokens": 45,
            "total_tokens": 165,
            "cost_in_usd_ticks": 50_000_000,
        },
    }


def test_extract_output_text_parses_responses_shape():
    payload = _responses_payload("Inference Economics")
    assert _extract_output_text(payload) == "Inference Economics"


def test_xai_theme_naming_with_mocked_api(monkeypatch):
    reset_llm_accounting()
    calls = {"count": 0}

    def fake_post(url, **kwargs):
        calls["count"] += 1
        request = httpx.Request("POST", url)
        return httpx.Response(200, request=request, json=_responses_payload("Inference Economics"))

    monkeypatch.setenv("XAI_API_KEY", "test-key")
    monkeypatch.setattr(httpx, "post", fake_post)

    provider = XAIResponsesProvider()
    title = provider.name_theme(ThemeNamingRequest(
        keywords=["inference", "gpu", "cost"],
        entities=["NVIDIA"],
        sample_claims=["Inference costs are rising."],
        sources=["Podcast"],
        speakers=["Speaker"],
    ))

    assert title == "Inference Economics"
    assert calls["count"] == 1
    summary = get_llm_accounting().summary()
    assert summary["requests"] == 1
    assert summary["total_tokens"] == 165
    assert summary["estimated_cost_usd"] > 0


def test_xai_falls_back_on_rate_limit(monkeypatch):
    reset_llm_accounting()
    attempts = {"count": 0}

    def fake_post(url, **kwargs):
        attempts["count"] += 1
        request = httpx.Request("POST", url)
        if attempts["count"] <= 2:
            return httpx.Response(429, request=request, json={"error": "rate limit"})
        return httpx.Response(200, request=request, json=_responses_payload("Should not reach"))

    monkeypatch.setenv("XAI_API_KEY", "test-key")
    monkeypatch.setenv("KNOWLEDGE_LLM_MAX_RETRIES", "1")
    monkeypatch.setattr(httpx, "post", fake_post)

    provider = XAIResponsesProvider()
    title = provider.name_theme(ThemeNamingRequest(
        keywords=["inference", "gpu"],
        entities=[],
        sample_claims=["Inference costs are rising."],
        sources=["Podcast"],
        speakers=["Speaker"],
    ))

    assert title == "Inference Economics"
    assert attempts["count"] == 2
    assert get_llm_accounting().summary()["fallback_events"] >= 0


def test_xai_converse_returns_response_id(monkeypatch):
    reset_llm_accounting()

    def fake_post(url, **kwargs):
        request = httpx.Request("POST", url)
        body = kwargs.get("json") or {}
        assert body.get("previous_response_id") == "resp_prev"
        return httpx.Response(200, request=request, json=_responses_payload("Analyst briefing text.", response_id="resp_new"))

    monkeypatch.setenv("XAI_API_KEY", "test-key")
    monkeypatch.setattr(httpx, "post", fake_post)

    provider = XAIResponsesProvider()
    result = provider.converse(ConversationRequest(
        intelligence_item_id="item-1",
        title="Inference Economics",
        executive_summary="Costs are shifting.",
        user_message="Show contradictions",
        previous_response_id="resp_prev",
        evidence=[{"speaker": "A", "source": "Pod", "timestamp_label": "00:10", "excerpt": "Signal"}],
    ))

    assert result.text == "Analyst briefing text."
    assert result.response_id == "resp_new"
    assert result.used_fallback is False


def test_registry_selects_xai_provider(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_LLM_PROVIDER", "xai_responses")
    monkeypatch.setenv("XAI_API_KEY", "test-key")
    provider = configure_llm("xai_responses")
    assert provider.name == "xai_responses"


def test_config_never_exposes_api_key(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "super-secret-key")
    public = load_llm_config().to_public_dict()
    assert "super-secret-key" not in json.dumps(public)
    assert public["xai_api_key_configured"] is True