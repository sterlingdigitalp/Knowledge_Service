"""OpenAI-compatible HTTP LLM provider (optional, API-key driven)."""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from .analyst_provider import AnalystLLMProvider
from .provider import ConversationRequest, ConversationResult, SummaryRequest, ThemeNamingRequest


class OpenAICompatibleProvider(AnalystLLMProvider):
    """Uses chat completions API when configured; falls back to analyst heuristics."""

    name = "openai_compatible"

    def __init__(self, model: str = "gpt-4o-mini", base_url: str | None = None, api_key: str | None = None):
        self.model = model
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._fallback = AnalystLLMProvider()

    def _available(self) -> bool:
        return bool(self.api_key)

    def name_theme(self, request: ThemeNamingRequest) -> str:
        if not self._available():
            return self._fallback.name_theme(request)
        prompt = (
            "Name this intelligence theme like a senior equity research analyst section title. "
            "Return only the title, 2-5 words, no quotes.\n"
            f"Keywords: {', '.join(request.keywords[:12])}\n"
            f"Entities: {', '.join(request.entities[:8])}\n"
            f"Sample claims: {' | '.join(request.sample_claims[:3])}"
        )
        result = self._chat(prompt, max_tokens=24)
        return result or self._fallback.name_theme(request)

    def executive_summary(self, request: SummaryRequest) -> str:
        if not self._available():
            return self._fallback.executive_summary(request)
        prompt = (
            "Write a concise executive summary as a senior research analyst. "
            "Explain what changed, why it matters, why now, and what to watch next. "
            "No transcript quotes, no fluff.\n"
            f"Theme: {request.title}\n"
            f"Sources: {', '.join(request.sources[:6])}\n"
            f"Speakers: {', '.join(request.speakers[:6])}\n"
            f"Novelty: {request.novelty_classification}\n"
            f"Importance: {request.importance_band}\n"
            f"Corroboration: {request.corroboration_count}\n"
            f"Claims: {' | '.join(request.claim_excerpts[:4])}"
        )
        result = self._chat(prompt, max_tokens=220)
        return result or self._fallback.executive_summary(request)

    def converse(self, request: ConversationRequest) -> ConversationResult:
        if not self._available():
            return self._fallback.converse(request)
        history = "\n".join(f"{m['role']}: {m['content']}" for m in request.conversation_history[-6:])
        prompt = (
            "You are a personal intelligence analyst. Answer with evidence-backed judgment.\n"
            f"Item: {request.title}\n"
            f"Summary: {request.executive_summary}\n"
            f"History:\n{history}\n"
            f"User: {request.user_message}"
        )
        result = self._chat(prompt, max_tokens=400)
        if result:
            return ConversationResult(text=result, provider=self.name)
        return self._fallback.converse(request)

    def _chat(self, prompt: str, max_tokens: int = 200) -> str:
        try:
            import httpx
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": 0.3,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            payload: Dict[str, Any] = response.json()
            return str(payload["choices"][0]["message"]["content"]).strip()
        except Exception:
            return ""