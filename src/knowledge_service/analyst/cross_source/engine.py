"""Cross-Source Intelligence — detect independent convergence."""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from ...intelligence.models import stable_id
from ...retrieval.embedding import cosine_similarity, embed_text
from ..models import Claim, CorroborationCluster, ScoredClaim


CLUSTER_THRESHOLD = 0.58


class CrossSourceEngine:
    """Detect when multiple trusted sources independently discuss the same topic."""

    def build_clusters(self, claims: Sequence[Claim]) -> List[CorroborationCluster]:
        if not claims:
            return []

        clusters: List[List[Claim]] = []
        assigned: Dict[str, int] = {}

        for claim in claims:
            embedding = claim.embedding or embed_text(claim.claim_text)
            cluster_index = None
            for index, members in enumerate(clusters):
                representative = members[0]
                rep_embedding = representative.embedding or embed_text(representative.claim_text)
                if cosine_similarity(embedding, rep_embedding) >= CLUSTER_THRESHOLD:
                    cluster_index = index
                    break
            if cluster_index is None:
                clusters.append([claim])
                assigned[claim.claim_id] = len(clusters) - 1
            else:
                clusters[cluster_index].append(claim)
                assigned[claim.claim_id] = cluster_index

        results: List[CorroborationCluster] = []
        for members in clusters:
            source_ids = sorted({member.source_id or member.episode_id for member in members})
            speakers = sorted({member.speaker for member in members if member.speaker})
            independent_sources = len({member.episode_id for member in members})
            if independent_sources < 2:
                continue

            topic_label = _topic_label(members)
            cluster_id = stable_id("cluster", topic_label, *source_ids[:3])
            corroboration_count = independent_sources - 1
            confidence = min(1.0, 0.45 + corroboration_count * 0.18)

            results.append(CorroborationCluster(
                cluster_id=cluster_id,
                topic_label=topic_label,
                claim_ids=[member.claim_id for member in members],
                source_ids=source_ids,
                speakers=speakers,
                corroboration_count=corroboration_count,
                confidence=round(confidence, 3),
                explanation=(
                    f"{independent_sources} independent sources ({', '.join(speakers[:4])}) "
                    f"converging on {topic_label}."
                ),
            ))
        return results

    def apply_corroboration(
        self,
        scored_claims: List[ScoredClaim],
        clusters: Sequence[CorroborationCluster],
    ) -> List[ScoredClaim]:
        cluster_by_claim = {}
        for cluster in clusters:
            for claim_id in cluster.claim_ids:
                cluster_by_claim[claim_id] = cluster

        updated: List[ScoredClaim] = []
        for item in scored_claims:
            cluster = cluster_by_claim.get(item.claim.claim_id)
            if cluster:
                item.corroboration_cluster_id = cluster.cluster_id
                item.corroboration_count = cluster.corroboration_count
            updated.append(item)
        return updated


def _topic_label(members: Sequence[Claim]) -> str:
    topics = [member.topic for member in members if member.topic and member.topic != "general"]
    if topics:
        return max(set(topics), key=topics.count)
    entities: List[str] = []
    for member in members:
        entities.extend(member.entities)
    if entities:
        return max(set(entities), key=entities.count)
    return members[0].claim_text[:60]