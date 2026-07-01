"""Persistent LLM enhancement cache — keyed by item, prompt version, and model."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ...intelligence.models import now_iso, stable_id
from ...intelligence.state import FileStateStore


PROMPT_VERSION = os.environ.get("KNOWLEDGE_LLM_PROMPT_VERSION", "5.1.2")
LLM_CACHE_FILE = "production/llm_cache.json"


@dataclass
class CachedBriefEnhancement:
    item_id: str
    theme_id: str
    claim_fingerprint: str
    prompt_version: str
    model: str
    title: str
    executive_summary: str
    why_it_matters: str
    provider: str
    cached_at: str

    def cache_key(self) -> str:
        return f"{self.item_id}:{self.prompt_version}:{self.model}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "theme_id": self.theme_id,
            "claim_fingerprint": self.claim_fingerprint,
            "prompt_version": self.prompt_version,
            "model": self.model,
            "title": self.title,
            "executive_summary": self.executive_summary,
            "why_it_matters": self.why_it_matters,
            "provider": self.provider,
            "cached_at": self.cached_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CachedBriefEnhancement":
        return cls(
            item_id=str(data.get("item_id") or ""),
            theme_id=str(data.get("theme_id") or ""),
            claim_fingerprint=str(data.get("claim_fingerprint") or ""),
            prompt_version=str(data.get("prompt_version") or ""),
            model=str(data.get("model") or ""),
            title=str(data.get("title") or ""),
            executive_summary=str(data.get("executive_summary") or ""),
            why_it_matters=str(data.get("why_it_matters") or ""),
            provider=str(data.get("provider") or ""),
            cached_at=str(data.get("cached_at") or ""),
        )


def claim_fingerprint(supporting_claim_ids: List[str]) -> str:
    if not supporting_claim_ids:
        return "no-claims"
    return stable_id(*sorted(supporting_claim_ids))


def is_cache_valid(
    entry: CachedBriefEnhancement,
    *,
    item_id: str,
    theme_id: str,
    supporting_claim_ids: List[str],
    prompt_version: str,
    model: str,
) -> bool:
    return (
        entry.item_id == item_id
        and entry.theme_id == theme_id
        and entry.claim_fingerprint == claim_fingerprint(supporting_claim_ids)
        and entry.prompt_version == prompt_version
        and entry.model == model
    )


class LLMEnhancementCache:
    """File-backed cache surviving restarts."""

    def __init__(self, state: FileStateStore):
        self.state = state
        (self.state.root / "production").mkdir(parents=True, exist_ok=True)

    def load_all(self) -> Dict[str, CachedBriefEnhancement]:
        raw = self.state.read_json(LLM_CACHE_FILE, {"entries": {}})
        entries = raw.get("entries") or {}
        return {
            key: CachedBriefEnhancement.from_dict(value)
            for key, value in entries.items()
        }

    def get(
        self,
        *,
        item_id: str,
        theme_id: str,
        supporting_claim_ids: List[str],
        prompt_version: str,
        model: str,
    ) -> Optional[CachedBriefEnhancement]:
        key = f"{item_id}:{prompt_version}:{model}"
        entry = self.load_all().get(key)
        if entry is None:
            return None
        if is_cache_valid(
            entry,
            item_id=item_id,
            theme_id=theme_id,
            supporting_claim_ids=supporting_claim_ids,
            prompt_version=prompt_version,
            model=model,
        ):
            return entry
        return None

    def put(self, entry: CachedBriefEnhancement) -> None:
        data = self.state.read_json(LLM_CACHE_FILE, {"entries": {}, "updated_at": ""})
        entries = data.setdefault("entries", {})
        entries[entry.cache_key()] = entry.to_dict()
        data["updated_at"] = now_iso()
        self.state.write_json(LLM_CACHE_FILE, data)

    def summary(self) -> Dict[str, Any]:
        entries = self.load_all()
        return {
            "entries": len(entries),
            "prompt_version": PROMPT_VERSION,
            "file": LLM_CACHE_FILE,
        }