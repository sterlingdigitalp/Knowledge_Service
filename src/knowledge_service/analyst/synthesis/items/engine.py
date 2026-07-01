"""Intelligence Item Engine — merge claims into coherent developments."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Sequence, Set

from ....intelligence.models import stable_id
from ...models import CorroborationCluster, ImportanceBand, NoveltyClass, ScoredClaim
from ..models import IntelligenceItem, Theme, ThemeEvolution


MIN_ITEM_CLAIMS = 2
MIN_THEME_CLAIMS = 3
MIN_ITEM_IMPORTANCE = 0.55


class IntelligenceItemEngine:
    """Transform claim clusters and themes into user-facing Intelligence Items."""

    def synthesize(
        self,
        scored_claims: Sequence[ScoredClaim],
        themes: Sequence[Theme],
        clusters: Sequence[CorroborationCluster],
        theme_evolutions: Sequence[ThemeEvolution],
    ) -> List[IntelligenceItem]:
        scored_by_id = {item.claim.claim_id: item for item in scored_claims}
        evolution_by_theme = {record.theme_id: record for record in theme_evolutions}
        cluster_by_claim: Dict[str, CorroborationCluster] = {}
        for cluster in clusters:
            for claim_id in cluster.claim_ids:
                cluster_by_claim[claim_id] = cluster

        items: List[IntelligenceItem] = []
        consumed_claims: Set[str] = set()

        for theme in themes:
            members = [scored_by_id[cid] for cid in theme.claim_ids if cid in scored_by_id]
            if len(members) < MIN_THEME_CLAIMS:
                continue
            item = self._build_item(
                members,
                theme=theme,
                evolution=evolution_by_theme.get(theme.theme_id),
                cluster_by_claim=cluster_by_claim,
            )
            if item.importance_score >= MIN_ITEM_IMPORTANCE:
                items.append(item)
                consumed_claims.update(theme.claim_ids)

        for cluster in clusters:
            members = [scored_by_id[cid] for cid in cluster.claim_ids if cid in scored_by_id and cid not in consumed_claims]
            if len(members) < MIN_ITEM_CLAIMS:
                continue
            pseudo_theme = Theme(
                theme_id=stable_id("theme-cluster", cluster.cluster_id),
                label=cluster.topic_label,
                claim_ids=cluster.claim_ids,
                keywords=[cluster.topic_label],
                entities=[],
                source_count=len({m.claim.episode_id for m in members}),
                speaker_count=len({m.claim.speaker for m in members}),
            )
            item = self._build_item(members, theme=pseudo_theme, evolution=None, cluster_by_claim=cluster_by_claim, cluster_id=cluster.cluster_id)
            if item.importance_score >= MIN_ITEM_IMPORTANCE and item.item_id not in {i.item_id for i in items}:
                items.append(item)
                consumed_claims.update(cluster.claim_ids)

        items.sort(key=lambda row: (row.importance_score, row.corroboration_count, row.claim_count), reverse=True)
        return _dedupe_items(items)

    def _build_item(
        self,
        members: List[ScoredClaim],
        *,
        theme: Theme,
        evolution: Optional[ThemeEvolution],
        cluster_by_claim: Dict[str, CorroborationCluster],
        cluster_id: Optional[str] = None,
    ) -> IntelligenceItem:
        members.sort(key=lambda item: item.importance.score, reverse=True)
        top = members[0]
        claims = [item.claim for item in members]

        sources = sorted({claim.podcast_name or claim.source_id for claim in claims if claim.podcast_name or claim.source_id})
        speakers = sorted({claim.speaker for claim in claims if claim.speaker and claim.speaker != "unknown"})
        profile_map: Dict[str, str] = {}
        for item in members:
            for rel in item.relevance:
                if rel.score >= 0.35:
                    profile_map[rel.profile_id] = rel.profile_name

        corroboration = max((item.corroboration_count for item in members), default=0)
        if not cluster_id:
            for claim_id in theme.claim_ids:
                cluster = cluster_by_claim.get(claim_id)
                if cluster:
                    cluster_id = cluster.cluster_id
                    corroboration = max(corroboration, cluster.corroboration_count)
                    break

        contradictions = []
        for item in members:
            for contradiction in item.contradictions:
                contradictions.append(contradiction.to_dict())

        novelty_scores = [item.novelty.score for item in members]
        importance_scores = [item.importance.score for item in members]
        avg_novelty = sum(novelty_scores) / len(novelty_scores)
        avg_importance = sum(importance_scores) / len(importance_scores)
        novelty_class = _dominant_novelty(members)
        importance_band = top.importance.band.value

        matched_keywords = theme.keywords[:5] + theme.entities[:3]
        why_surfaced = f"Matched: {', '.join(matched_keywords)}" if matched_keywords else f"Theme: {theme.label}"
        if evolution:
            why_surfaced += f". Evolution: {evolution.state.value} — {evolution.explanation}"

        executive = _executive_summary(theme.label, sources, speakers, top.claim.claim_text, len(members))
        why_matters = _why_matters(members, corroboration, contradictions)

        evidence = []
        citations = []
        for item in members[:6]:
            claim = item.claim
            evidence.append({
                "claim_id": claim.claim_id,
                "speaker": claim.speaker,
                "source": claim.podcast_name,
                "excerpt": claim.evidence[:200],
                "timestamp_label": claim.timestamp_label,
            })
            citations.append({
                "speaker": claim.speaker,
                "source": claim.podcast_name,
                "timestamp_label": claim.timestamp_label,
                "url": claim.transcript_reference or claim.source_url,
            })

        historical = []
        if evolution and evolution.prior_theme_id:
            historical.append({
                "prior_theme_id": evolution.prior_theme_id,
                "state": evolution.state.value,
                "explanation": evolution.explanation,
                "similarity": evolution.similarity_to_prior,
            })

        confidence = min(0.99, 0.4 + avg_importance * 0.3 + min(corroboration, 4) * 0.08 + len(sources) * 0.05)
        star_rating = _star_rating(avg_importance)

        return IntelligenceItem(
            item_id=stable_id("intel-item", theme.label, theme.theme_id),
            title=theme.label,
            executive_summary=executive,
            why_surfaced=why_surfaced,
            why_it_matters=why_matters,
            novelty_score=round(avg_novelty, 3),
            novelty_classification=novelty_class,
            importance_score=round(avg_importance, 3),
            importance_band=importance_band,
            confidence=round(confidence, 3),
            corroboration_count=corroboration,
            contradiction_count=len(contradictions),
            theme_id=theme.theme_id,
            theme_label=theme.label,
            profile_ids=list(profile_map.keys()),
            profile_names=list(profile_map.values()),
            supporting_claim_ids=[claim.claim_id for claim in claims],
            supporting_evidence=evidence,
            timestamped_citations=citations,
            speakers=speakers[:8],
            sources=sources[:8],
            contradictions=contradictions[:5],
            historical_developments=historical,
            theme_evolution=evolution,
            cluster_id=cluster_id,
            star_rating=star_rating,
            claim_count=len(claims),
        )


def _executive_summary(label: str, sources: List[str], speakers: List[str], lead_claim: str, claim_count: int) -> str:
    source_phrase = f"{len(sources)} independent source{'s' if len(sources) != 1 else ''}"
    if speakers:
        named = ", ".join(speakers[:4])
        speaker_phrase = f"including {named}"
    else:
        speaker_phrase = "across the monitored corpus"
    lead = lead_claim[:160].rsplit(" ", 1)[0] + "..." if len(lead_claim) > 160 else lead_claim
    return (
        f"{label}: {source_phrase} ({speaker_phrase}) discussed this development "
        f"across {claim_count} related claims. Key signal: {lead}"
    )


def _why_matters(members: List[ScoredClaim], corroboration: int, contradictions: List) -> str:
    top = members[0]
    parts = [top.importance.explanation]
    if corroboration:
        parts.append(f"Corroborated by {corroboration} additional independent source(s).")
    if contradictions:
        parts.append(f"{len(contradictions)} contradiction(s) surfaced — compare positions.")
    if top.novelty.classification == NoveltyClass.CONTRADICTION:
        parts.append("Conflicting guidance detected within this theme.")
    return " ".join(parts)


def _dominant_novelty(members: List[ScoredClaim]) -> str:
    counts: Dict[str, int] = defaultdict(int)
    for item in members:
        counts[item.novelty.classification.value] += 1
    return max(counts, key=counts.get)


def _star_rating(importance: float) -> int:
    if importance >= 0.85:
        return 5
    if importance >= 0.72:
        return 4
    if importance >= 0.58:
        return 3
    if importance >= 0.45:
        return 2
    return 1


def _dedupe_items(items: List[IntelligenceItem]) -> List[IntelligenceItem]:
    seen_titles: set[str] = set()
    unique: List[IntelligenceItem] = []
    for item in items:
        key = item.title.lower()
        if key in seen_titles:
            continue
        seen_titles.add(key)
        unique.append(item)
    return unique