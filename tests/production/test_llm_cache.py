from knowledge_service.intelligence.state import FileStateStore
from knowledge_service.production.llm.cache import (
    PROMPT_VERSION,
    CachedBriefEnhancement,
    LLMEnhancementCache,
    claim_fingerprint,
    is_cache_valid,
)


def test_cache_hit_when_claims_unchanged(tmp_path):
    state = FileStateStore(tmp_path)
    cache = LLMEnhancementCache(state)
    entry = CachedBriefEnhancement(
        item_id="item-1",
        theme_id="theme-1",
        claim_fingerprint=claim_fingerprint(["c1", "c2"]),
        prompt_version=PROMPT_VERSION,
        model="grok-4.3",
        title="Inference Economics",
        executive_summary="Costs are shifting.",
        why_it_matters="Portfolio relevance.",
        provider="xai_responses",
        cached_at="2026-07-01T00:00:00Z",
    )
    cache.put(entry)
    loaded = cache.get(
        item_id="item-1",
        theme_id="theme-1",
        supporting_claim_ids=["c2", "c1"],
        prompt_version=PROMPT_VERSION,
        model="grok-4.3",
    )
    assert loaded is not None
    assert loaded.title == "Inference Economics"


def test_cache_miss_when_theme_changes(tmp_path):
    state = FileStateStore(tmp_path)
    cache = LLMEnhancementCache(state)
    cache.put(CachedBriefEnhancement(
        item_id="item-1",
        theme_id="theme-1",
        claim_fingerprint=claim_fingerprint(["c1"]),
        prompt_version=PROMPT_VERSION,
        model="grok-4.3",
        title="Old",
        executive_summary="Old summary",
        why_it_matters="Old why",
        provider="xai_responses",
        cached_at="2026-07-01T00:00:00Z",
    ))
    loaded = cache.get(
        item_id="item-1",
        theme_id="theme-2",
        supporting_claim_ids=["c1"],
        prompt_version=PROMPT_VERSION,
        model="grok-4.3",
    )
    assert loaded is None


def test_cache_survives_restart(tmp_path):
    state = FileStateStore(tmp_path)
    cache = LLMEnhancementCache(state)
    cache.put(CachedBriefEnhancement(
        item_id="item-9",
        theme_id="theme-9",
        claim_fingerprint=claim_fingerprint(["c9"]),
        prompt_version=PROMPT_VERSION,
        model="grok-4.3",
        title="Cached",
        executive_summary="Persisted",
        why_it_matters="Why",
        provider="xai_responses",
        cached_at="2026-07-01T00:00:00Z",
    ))
    reloaded = LLMEnhancementCache(FileStateStore(tmp_path))
    assert reloaded.get(
        item_id="item-9",
        theme_id="theme-9",
        supporting_claim_ids=["c9"],
        prompt_version=PROMPT_VERSION,
        model="grok-4.3",
    ) is not None


def test_is_cache_valid_detects_prompt_version_change():
    entry = CachedBriefEnhancement(
        item_id="a",
        theme_id="t",
        claim_fingerprint="fp",
        prompt_version="5.1.1",
        model="grok-4.3",
        title="x",
        executive_summary="y",
        why_it_matters="z",
        provider="xai_responses",
        cached_at="now",
    )
    assert not is_cache_valid(
        entry,
        item_id="a",
        theme_id="t",
        supporting_claim_ids=[],
        prompt_version="5.1.2",
        model="grok-4.3",
    )