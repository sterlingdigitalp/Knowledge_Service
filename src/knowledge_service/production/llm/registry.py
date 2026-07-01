"""LLM provider registry."""

from __future__ import annotations

import os
from typing import Optional

from ..store import ProductionStore
from ...intelligence.state import FileStateStore
from .accounting import get_llm_accounting, reset_llm_accounting
from .analyst_provider import AnalystLLMProvider
from .config import load_llm_config
from .openai_compatible import OpenAICompatibleProvider
from .provider import LLMProvider
from .xai_responses import XAIResponsesProvider


_active_llm: Optional[LLMProvider] = None
_persistence_bound = False


def _build_provider(name: str) -> LLMProvider:
    if name == "xai_responses":
        config = load_llm_config()
        fallback = _build_provider(config.fallback_provider)
        return XAIResponsesProvider(config=config, fallback=fallback)
    if name == "openai_compatible" and os.environ.get("OPENAI_API_KEY"):
        return OpenAICompatibleProvider()
    return AnalystLLMProvider()


def _bind_accounting_persistence(state_dir: str | None = None) -> None:
    global _persistence_bound
    if _persistence_bound:
        return
    if not state_dir:
        return
    store = ProductionStore(FileStateStore(state_dir))
    get_llm_accounting().bind_persistence(store.append_llm_usage)
    _persistence_bound = True


def get_llm_provider(name: str | None = None, *, state_dir: str | None = None) -> LLMProvider:
    global _active_llm
    _bind_accounting_persistence(state_dir)
    selected = name or os.environ.get("KNOWLEDGE_LLM_PROVIDER", "analyst_heuristic")
    if _active_llm is not None and _active_llm.name == selected:
        return _active_llm
    _active_llm = _build_provider(selected)
    return _active_llm


def configure_llm(name: str, *, state_dir: str | None = None) -> LLMProvider:
    global _active_llm, _persistence_bound
    _active_llm = None
    reset_llm_accounting()
    _persistence_bound = False
    return get_llm_provider(name, state_dir=state_dir)


def llm_runtime_summary(provider: LLMProvider | None = None) -> dict:
    active = provider or _active_llm or AnalystLLMProvider()
    config = load_llm_config()
    metrics = active.runtime_metrics() if hasattr(active, "runtime_metrics") else {"provider": active.name}
    return {
        "config": config.to_public_dict(),
        "active_provider": active.name,
        "metrics": metrics,
        "accounting": get_llm_accounting().summary(),
        "recent_events": get_llm_accounting().recent(10),
    }