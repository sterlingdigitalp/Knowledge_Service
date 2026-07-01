"""Interactive deep-dive artifacts for surfaced intelligence claims."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .claims import IntelligenceClaim
from .correlation import CrossSourceCluster
from .importance import ImportanceResult
from .models import now_iso, stable_id
from .novelty import NoveltyResult
from .relevance import RelevanceResult
from .state import FileStateStore


DEEP_DIVES_FILE = "deep_dives.jsonl"
LATEST_DEEP_DIVES_FILE = "latest_deep_dives.json"


@dataclass
class InteractiveDeepDive:
    deep_dive_id: str
    claim_id: str
    profile_id: str
    generated_at: str
    title: str
    focal_claim: Dict[str, Any]
    intelligence: Dict[str, Any]
    surrounding_context: Dict[str, Any]
    corroborating_evidence: List[Dict[str, Any]] = field(default_factory=list)
    contradictory_evidence: List[Dict[str, Any]] = field(default_factory=list)
    related_claims: List[Dict[str, Any]] = field(default_factory=list)
    evidence_trail: List[Dict[str, Any]] = field(default_factory=list)
    navigation: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deep_dive_id": self.deep_dive_id,
            "claim_id": self.claim_id,
            "profile_id": self.profile_id,
            "generated_at": self.generated_at,
            "title": self.title,
            "focal_claim": dict(self.focal_claim),
            "intelligence": dict(self.intelligence),
            "surrounding_context": dict(self.surrounding_context),
            "corroborating_evidence": list(self.corroborating_evidence),
            "contradictory_evidence": list(self.contradictory_evidence),
            "related_claims": list(self.related_claims),
            "evidence_trail": list(self.evidence_trail),
            "navigation": list(self.navigation),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InteractiveDeepDive":
        return cls(
            deep_dive_id=str(data.get("deep_dive_id") or ""),
            claim_id=str(data.get("claim_id") or ""),
            profile_id=str(data.get("profile_id") or ""),
            generated_at=str(data.get("generated_at") or now_iso()),
            title=str(data.get("title") or ""),
            focal_claim=dict(data.get("focal_claim") or {}),
            intelligence=dict(data.get("intelligence") or {}),
            surrounding_context=dict(data.get("surrounding_context") or {}),
            corroborating_evidence=list(data.get("corroborating_evidence") or []),
            contradictory_evidence=list(data.get("contradictory_evidence") or []),
            related_claims=list(data.get("related_claims") or []),
            evidence_trail=list(data.get("evidence_trail") or []),
            navigation=list(data.get("navigation") or []),
        )


class InteractiveDeepDiveGenerator:
    def __init__(self, state: FileStateStore):
        self.state = state

    def generate(
        self,
        claims: List[IntelligenceClaim],
        novelty: List[NoveltyResult],
        relevance: List[RelevanceResult],
        importance: List[ImportanceResult],
        clusters: List[CrossSourceCluster],
        max_deep_dives: int = 10,
        selected_claim_ids: Optional[List[str]] = None,
    ) -> List[InteractiveDeepDive]:
        claims_by_id = {claim.claim_id: claim for claim in claims}
        novelty_by_id = {item.claim_id: item for item in novelty}
        relevance_by_key = {(item.claim_id, item.profile_id): item for item in relevance}
        clusters_by_claim = _clusters_by_claim(clusters)
        selected = set(selected_claim_ids or [])
        ranked = sorted(importance, key=lambda item: item.importance_score, reverse=True)
        dives: List[InteractiveDeepDive] = []
        seen: set[tuple[str, str]] = set()
        for score in ranked:
            if selected and score.claim_id not in selected:
                continue
            key = (score.claim_id, score.profile_id)
            if key in seen:
                continue
            claim = claims_by_id.get(score.claim_id)
            nov = novelty_by_id.get(score.claim_id)
            rel = relevance_by_key.get(key)
            if not claim or not nov or not rel:
                continue
            dives.append(_deep_dive(
                claim=claim,
                novelty=nov,
                relevance=rel,
                importance=score,
                cluster=clusters_by_claim.get(score.claim_id),
                claims_by_id=claims_by_id,
                novelty_by_id=novelty_by_id,
            ))
            seen.add(key)
            if len(dives) >= max_deep_dives:
                break
        self.state.write_jsonl(DEEP_DIVES_FILE, [dive.to_dict() for dive in dives])
        self.state.write_json(LATEST_DEEP_DIVES_FILE, {"generated_at": now_iso(), "deep_dives": [dive.to_dict() for dive in dives]})
        return dives

    def load_latest(self) -> List[InteractiveDeepDive]:
        data = self.state.read_json(LATEST_DEEP_DIVES_FILE, {"deep_dives": []})
        return [InteractiveDeepDive.from_dict(item) for item in data.get("deep_dives", [])]


def _deep_dive(
    claim: IntelligenceClaim,
    novelty: NoveltyResult,
    relevance: RelevanceResult,
    importance: ImportanceResult,
    cluster: Optional[CrossSourceCluster],
    claims_by_id: Dict[str, IntelligenceClaim],
    novelty_by_id: Dict[str, NoveltyResult],
) -> InteractiveDeepDive:
    generated_at = now_iso()
    related = _related_claims(claim, novelty, cluster, claims_by_id)
    corroborating = _corroborating_evidence(claim, cluster, claims_by_id)
    contradictory = _contradictory_evidence(claim, novelty, cluster, claims_by_id, novelty_by_id)
    evidence_trail = [_evidence_entry(claim, "focal")]
    evidence_trail.extend(corroborating[:5])
    evidence_trail.extend(contradictory[:5])
    return InteractiveDeepDive(
        deep_dive_id=stable_id("deep_dive", claim.claim_id, importance.profile_id, generated_at),
        claim_id=claim.claim_id,
        profile_id=importance.profile_id,
        generated_at=generated_at,
        title=claim.claim_text[:120],
        focal_claim={
            "claim_id": claim.claim_id,
            "claim_text": claim.claim_text,
            "topic": claim.topic,
            "source_id": claim.source_id,
            "source_name": claim.source_name,
            "speaker": claim.speaker or "unknown",
            "timestamp_start": claim.timestamp_start,
            "timestamp_end": claim.timestamp_end,
            "timestamped_source_url": claim.timestamped_source_url,
            "evidence": dict(claim.evidence),
            "transcript_reference": dict(claim.transcript_reference),
        },
        intelligence={
            "what_is_new": f"{novelty.novelty_label}: {novelty.explanation}",
            "why_user_cares": relevance.explanation,
            "why_it_matters": importance.explanation,
            "importance_score": importance.importance_score,
            "importance_band": importance.importance_band,
            "components": dict(importance.components),
            "novelty_score": novelty.novelty_score,
            "relevance_score": relevance.relevance_score,
        },
        surrounding_context={
            "supporting_context": claim.supporting_context,
            "transcript_reference": dict(claim.transcript_reference),
            "nearest_prior_claim_ids": list(novelty.nearest_prior_claim_ids),
        },
        corroborating_evidence=corroborating,
        contradictory_evidence=contradictory,
        related_claims=related,
        evidence_trail=evidence_trail,
        navigation=[
            {"action": "open_transcript", "target": claim.timestamped_source_url, "label": "Open timestamped source"},
            {"action": "show_related_claims", "target": [item["claim_id"] for item in related], "label": "Compare related claims"},
            {"action": "show_evidence_trail", "target": [item["claim_id"] for item in evidence_trail], "label": "Audit evidence trail"},
            {"action": "show_profile_scores", "target": importance.profile_id, "label": "Explain profile relevance"},
        ],
    )


def _related_claims(
    claim: IntelligenceClaim,
    novelty: NoveltyResult,
    cluster: Optional[CrossSourceCluster],
    claims_by_id: Dict[str, IntelligenceClaim],
) -> List[Dict[str, Any]]:
    related_ids: List[str] = []
    if cluster:
        related_ids.extend([claim_id for claim_id in cluster.claim_ids if claim_id != claim.claim_id])
    related_ids.extend([claim_id for claim_id in novelty.nearest_prior_claim_ids if claim_id != claim.claim_id])
    output = []
    seen = set()
    for claim_id in related_ids:
        if claim_id in seen:
            continue
        related = claims_by_id.get(claim_id)
        if not related:
            continue
        output.append(_evidence_entry(related, "related"))
        seen.add(claim_id)
    return output[:12]


def _corroborating_evidence(
    claim: IntelligenceClaim,
    cluster: Optional[CrossSourceCluster],
    claims_by_id: Dict[str, IntelligenceClaim],
) -> List[Dict[str, Any]]:
    if not cluster:
        return []
    output = []
    focal_source = claim.source_id or claim.source_name
    for claim_id in cluster.claim_ids:
        if claim_id == claim.claim_id:
            continue
        other = claims_by_id.get(claim_id)
        if not other:
            continue
        other_source = other.source_id or other.source_name
        relation = "corroborating" if other_source != focal_source else "same_source_related"
        output.append(_evidence_entry(other, relation))
    return output[:12]


def _contradictory_evidence(
    claim: IntelligenceClaim,
    novelty: NoveltyResult,
    cluster: Optional[CrossSourceCluster],
    claims_by_id: Dict[str, IntelligenceClaim],
    novelty_by_id: Dict[str, NoveltyResult],
) -> List[Dict[str, Any]]:
    contradiction_ids = []
    if novelty.novelty_label == "contradiction_candidate":
        contradiction_ids.extend(novelty.nearest_prior_claim_ids)
    if cluster:
        contradiction_ids.extend([claim_id for claim_id in cluster.contradictions if claim_id != claim.claim_id])
        contradiction_ids.extend([
            claim_id for claim_id in cluster.claim_ids
            if novelty_by_id.get(claim_id) and novelty_by_id[claim_id].novelty_label == "contradiction_candidate"
        ])
    output = []
    seen = set()
    for claim_id in contradiction_ids:
        if claim_id in seen or claim_id == claim.claim_id:
            continue
        other = claims_by_id.get(claim_id)
        if not other:
            continue
        output.append(_evidence_entry(other, "contradiction_candidate"))
        seen.add(claim_id)
    return output[:12]


def _evidence_entry(claim: IntelligenceClaim, relation: str) -> Dict[str, Any]:
    return {
        "relation": relation,
        "claim_id": claim.claim_id,
        "claim_text": claim.claim_text,
        "source_id": claim.source_id,
        "source_name": claim.source_name,
        "speaker": claim.speaker or "unknown",
        "timestamp_start": claim.timestamp_start,
        "timestamp_end": claim.timestamp_end,
        "timestamped_source_url": claim.timestamped_source_url,
        "quote": (claim.evidence or {}).get("quote") or claim.claim_text,
        "transcript_reference": dict(claim.transcript_reference),
        "acquisition_route": claim.acquisition_route,
        "route_confidence": claim.route_confidence,
    }


def _clusters_by_claim(clusters: List[CrossSourceCluster]) -> Dict[str, CrossSourceCluster]:
    output: Dict[str, CrossSourceCluster] = {}
    for cluster in clusters:
        for claim_id in cluster.claim_ids:
            output[claim_id] = cluster
    return output
