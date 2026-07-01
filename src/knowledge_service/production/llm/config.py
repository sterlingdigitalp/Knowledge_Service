"""LLM provider configuration from environment — never serializes secrets."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict


SECRET_ENV_KEYS = frozenset({
    "XAI_API_KEY",
    "OPENAI_API_KEY",
})


@dataclass(frozen=True)
class LLMConfig:
    provider: str = "analyst_heuristic"
    fallback_provider: str = "analyst_heuristic"
    model: str = "grok-4.3"
    base_url: str = "https://api.x.ai/v1"
    timeout_seconds: float = 45.0
    max_retries: int = 3
    retry_backoff_seconds: float = 1.5
    reasoning_effort: str = "low"
    temperature: float = 0.3
    max_live_llm_items: int = 5
    max_live_llm_calls_per_run: int = 20
    maximum_live_llm_runtime_seconds: float = 300.0
    prompt_version: str = "5.1.2"

    @property
    def xai_api_key_configured(self) -> bool:
        return bool(os.environ.get("XAI_API_KEY"))

    @property
    def openai_api_key_configured(self) -> bool:
        return bool(os.environ.get("OPENAI_API_KEY"))

    def to_public_dict(self) -> Dict[str, Any]:
        """Safe for logs, inspector output, and certification artifacts."""
        return {
            "provider": self.provider,
            "fallback_provider": self.fallback_provider,
            "model": self.model,
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "reasoning_effort": self.reasoning_effort,
            "temperature": self.temperature,
            "xai_api_key_configured": self.xai_api_key_configured,
            "openai_api_key_configured": self.openai_api_key_configured,
            "max_live_llm_items": self.max_live_llm_items,
            "max_live_llm_calls_per_run": self.max_live_llm_calls_per_run,
            "maximum_live_llm_runtime_seconds": self.maximum_live_llm_runtime_seconds,
            "prompt_version": self.prompt_version,
        }


def load_llm_config() -> LLMConfig:
    return LLMConfig(
        provider=os.environ.get("KNOWLEDGE_LLM_PROVIDER", "analyst_heuristic"),
        fallback_provider=os.environ.get("KNOWLEDGE_LLM_FALLBACK_PROVIDER", "analyst_heuristic"),
        model=os.environ.get("KNOWLEDGE_LLM_MODEL", "grok-4.3"),
        base_url=(os.environ.get("XAI_BASE_URL") or "https://api.x.ai/v1").rstrip("/"),
        timeout_seconds=float(os.environ.get("KNOWLEDGE_LLM_TIMEOUT_SECONDS", "45")),
        max_retries=int(os.environ.get("KNOWLEDGE_LLM_MAX_RETRIES", "3")),
        retry_backoff_seconds=float(os.environ.get("KNOWLEDGE_LLM_RETRY_BACKOFF_SECONDS", "1.5")),
        reasoning_effort=os.environ.get("KNOWLEDGE_LLM_REASONING_EFFORT", "low"),
        temperature=float(os.environ.get("KNOWLEDGE_LLM_TEMPERATURE", "0.3")),
        max_live_llm_items=int(os.environ.get("KNOWLEDGE_LLM_MAX_ITEMS", "5")),
        max_live_llm_calls_per_run=int(os.environ.get("KNOWLEDGE_LLM_MAX_CALLS", "20")),
        maximum_live_llm_runtime_seconds=float(os.environ.get("KNOWLEDGE_LLM_MAX_RUNTIME_SECONDS", "300")),
        prompt_version=os.environ.get("KNOWLEDGE_LLM_PROMPT_VERSION", "5.1.2"),
    )


def redact_secrets(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Remove secret-bearing keys from nested dicts before persistence."""
    cleaned: Dict[str, Any] = {}
    for key, value in payload.items():
        if key in SECRET_ENV_KEYS or "api_key" in key.lower() and key != "api_key_configured":
            continue
        if isinstance(value, dict):
            cleaned[key] = redact_secrets(value)
        elif isinstance(value, list):
            cleaned[key] = [
                redact_secrets(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            cleaned[key] = value
    return cleaned