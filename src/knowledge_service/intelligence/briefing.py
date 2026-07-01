"""Morning Intelligence Brief generation for Phase 4."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .claims import IntelligenceClaim
from .correlation import CrossSourceCluster
from .importance import ImportanceResult
from .models import IntelligenceProfile, now_iso, stable_id
from .novelty import NoveltyResult
from .relevance import RelevanceResult
from .state import FileStateStore


MORNING_BRIEFS_FILE = "morning_briefs.jsonl"
LATEST_MORNING_BRIEF_FILE = "latest_morning_brief.json"


@dataclass
class BriefItem:
    claim_id: str
    profile_id: str
    profile_name: str
    claim_text: str
    importance_score: float
    importance_band: str
    novelty_label: str
    what_is_new: str
    why_user_cares: str
    why_it_matters: str
    where_evidence_is: Dict[str, Any]
    related_claim_ids: List[str] = field(default_factory=list)
    corroborating_sources: List[str] = field(default_factory=list)
    contradictory_claim_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "profile_id": self.profile_id,
            "profile_name": self.profile_name,
            "claim_text": self.claim_text,
            "importance_score": self.importance_score,
            "importance_band": self.importance_band,
            "novelty_label": self.novelty_label,
            "what_is_new": self.what_is_new,
            "why_user_cares": self.why_user_cares,
            "why_it_matters": self.why_it_matters,
            "where_evidence_is": dict(self.where_evidence_is),
            "related_claim_ids": list(self.related_claim_ids),
            "corroborating_sources": list(self.corroborating_sources),
            "contradictory_claim_ids": list(self.contradictory_claim_ids),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BriefItem":
        return cls(
            claim_id=str(data.get("claim_id") or ""),
            profile_id=str(data.get("profile_id") or ""),
            profile_name=str(data.get("profile_name") or ""),
            claim_text=str(data.get("claim_text") or ""),
            importance_score=float(data.get("importance_score", 0.0)),
            importance_band=str(data.get("importance_band") or "low"),
            novelty_label=str(data.get("novelty_label") or "unknown"),
            what_is_new=str(data.get("what_is_new") or ""),
            why_user_cares=str(data.get("why_user_cares") or ""),
            why_it_matters=str(data.get("why_it_matters") or ""),
            where_evidence_is=dict(data.get("where_evidence_is") or {}),
            related_claim_ids=list(data.get("related_claim_ids") or []),
            corroborating_sources=list(data.get("corroborating_sources") or []),
            contradictory_claim_ids=list(data.get("contradictory_claim_ids") or []),
        )


@dataclass
class MorningBrief:
    brief_id: str
    generated_at: str
    sections: List[Dict[str, Any]]
    item_count: int
    estimated_read_seconds: int
    source_claim_count: int
    profile_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "brief_id": self.brief_id,
            "generated_at": self.generated_at,
            "sections": list(self.sections),
            "item_count": self.item_count,
            "estimated_read_seconds": self.estimated_read_seconds,
            "source_claim_count": self.source_claim_count,
            "profile_count": self.profile_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MorningBrief":
        return cls(
            brief_id=str(data.get("brief_id") or ""),
            generated_at=str(data.get("generated_at") or now_iso()),
            sections=list(data.get("sections") or []),
            item_count=int(data.get("item_count", 0)),
            estimated_read_seconds=int(data.get("estimated_read_seconds", 0)),
            source_claim_count=int(data.get("source_claim_count", 0)),
            profile_count=int(data.get("profile_count", 0)),
        )


class MorningBriefGenerator:
    def __init__(self, state: FileStateStore):
        self.state = state

    def generate(
        self,
        profiles: List[IntelligenceProfile],
        claims: List[IntelligenceClaim],
        novelty: List[NoveltyResult],
        relevance: List[RelevanceResult],
        importance: List[ImportanceResult],
        clusters: List[CrossSourceCluster],
        max_items_per_profile: int = 5,
        minimum_importance: float = 0.35,
    ) -> MorningBrief:
        claims_by_id = {claim.claim_id: claim for claim in claims}
        novelty_by_id = {item.claim_id: item for item in novelty}
        relevance_by_key = {(item.claim_id, item.profile_id): item for item in relevance}
        clusters_by_claim = _clusters_by_claim(clusters)
        sections: List[Dict[str, Any]] = []
        item_count = 0

        for profile in profiles:
            ranked = sorted(
                [item for item in importance if item.profile_id == profile.profile_id],
                key=lambda item: item.importance_score,
                reverse=True,
            )
            selected = [item for item in ranked if item.importance_score >= minimum_importance][:max_items_per_profile]
            if not selected:
                selected = ranked[:max_items_per_profile]

            items = []
            seen_claims: set[str] = set()
            for score in selected:
                if score.claim_id in seen_claims:
                    continue
                claim = claims_by_id.get(score.claim_id)
                nov = novelty_by_id.get(score.claim_id)
                rel = relevance_by_key.get((score.claim_id, profile.profile_id))
                if not claim or not nov or not rel:
                    continue
                items.append(_brief_item(profile, claim, nov, rel, score, clusters_by_claim.get(score.claim_id)).to_dict())
                seen_claims.add(score.claim_id)
            item_count += len(items)
            sections.append({
                "profile_id": profile.profile_id,
                "profile_name": profile.name,
                "items": items,
            })

        generated_at = now_iso()
        brief = MorningBrief(
            brief_id=stable_id("morning_brief", generated_at, len(claims), item_count),
            generated_at=generated_at,
            sections=sections,
            item_count=item_count,
            estimated_read_seconds=max(15, min(60, item_count * 12)),
            source_claim_count=len(claims),
            profile_count=len(profiles),
        )
        self.state.append_jsonl(MORNING_BRIEFS_FILE, [brief.to_dict()])
        self.state.write_json(LATEST_MORNING_BRIEF_FILE, brief.to_dict())
        return brief

    def load_latest(self) -> Optional[MorningBrief]:
        data = self.state.read_json(LATEST_MORNING_BRIEF_FILE, None)
        return MorningBrief.from_dict(data) if data else None


def generate_morning_brief_markdown(brief: MorningBrief) -> str:
    lines = ["# Morning Intelligence Brief", "", f"Generated: {brief.generated_at}", f"Estimated read: {brief.estimated_read_seconds}s", ""]
    for section in brief.sections:
        lines.extend([f"## {section.get('profile_name') or section.get('profile_id')}", ""])
        items = section.get("items") or []
        if not items:
            lines.append("- No claims cleared the current attention threshold.")
            lines.append("")
            continue
        for item in items:
            evidence = item.get("where_evidence_is") or {}
            source = evidence.get("source_name") or evidence.get("source_id") or "unknown source"
            timestamp = _format_timestamp(evidence.get("timestamp_start"))
            lines.append(f"- {item['claim_text']}")
            lines.append(f"  - What is new: {item['what_is_new']}")
            lines.append(f"  - Why you care: {item['why_user_cares']}")
            lines.append(f"  - Why it matters: {item['why_it_matters']}")
            lines.append(f"  - Evidence: {source}, {evidence.get('speaker') or 'unknown'}, {timestamp}, {evidence.get('timestamped_source_url') or evidence.get('source_url')}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _brief_item(
    profile: IntelligenceProfile,
    claim: IntelligenceClaim,
    novelty: NoveltyResult,
    relevance: RelevanceResult,
    importance: ImportanceResult,
    cluster: Optional[CrossSourceCluster],
) -> BriefItem:
    related_claim_ids = []
    corroborating_sources = []
    contradictory_claim_ids = []
    if cluster:
        related_claim_ids = [claim_id for claim_id in cluster.claim_ids if claim_id != claim.claim_id][:8]
        corroborating_sources = [source for source in cluster.sources if source and source not in {claim.source_id, claim.source_name}]
        contradictory_claim_ids = [claim_id for claim_id in cluster.contradictions if claim_id != claim.claim_id]
    why_it_matters = (
        f"{importance.importance_band} importance ({importance.importance_score:.2f}) from "
        f"{importance.explanation}"
    )
    if corroborating_sources:
        why_it_matters += f"; corroborated by {len(corroborating_sources)} other source(s)"
    return BriefItem(
        claim_id=claim.claim_id,
        profile_id=profile.profile_id,
        profile_name=profile.name,
        claim_text=claim.claim_text,
        importance_score=importance.importance_score,
        importance_band=importance.importance_band,
        novelty_label=novelty.novelty_label,
        what_is_new=f"{novelty.novelty_label}: {novelty.explanation}",
        why_user_cares=f"For {profile.name}: {relevance.explanation}",
        why_it_matters=why_it_matters,
        where_evidence_is=_evidence_for_claim(claim),
        related_claim_ids=related_claim_ids,
        corroborating_sources=corroborating_sources,
        contradictory_claim_ids=contradictory_claim_ids,
    )


def _evidence_for_claim(claim: IntelligenceClaim) -> Dict[str, Any]:
    return {
        "source_id": claim.source_id,
        "source_name": claim.source_name,
        "speaker": claim.speaker or "unknown",
        "timestamp_start": claim.timestamp_start,
        "timestamp_end": claim.timestamp_end,
        "timestamped_source_url": claim.timestamped_source_url,
        "quote": (claim.evidence or {}).get("quote") or claim.claim_text,
        "citation_quote": (claim.evidence or {}).get("citation_quote"),
        "citation_context": (claim.evidence or {}).get("citation_context"),
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


def _format_timestamp(value: Any) -> str:
    if value is None:
        return "timestamp unknown"
    try:
        seconds = int(float(value))
    except (TypeError, ValueError):
        return str(value)
    return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"
