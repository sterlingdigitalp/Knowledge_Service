"""Relevance Engine — evaluate every claim against every Intelligence Profile."""

from __future__ import annotations

from typing import List, Sequence

from ...intelligence.models import IntelligenceProfile
from ...retrieval.embedding import cosine_similarity, embed_text
from ..models import Claim, RelevanceResult


class RelevanceEngine:
    """Score whether a claim matters to each profile — not merely whether it is interesting."""

    def score(self, claim: Claim, profiles: Sequence[IntelligenceProfile]) -> List[RelevanceResult]:
        if not claim.embedding:
            claim.embedding = embed_text(claim.claim_text)

        results: List[RelevanceResult] = []
        haystack = f"{claim.claim_text} {claim.topic} {' '.join(claim.entities)} {claim.supporting_context}".lower()

        for profile in profiles:
            if not profile.enabled:
                continue

            matched_interests = [interest for interest in profile.interests if interest.lower() in haystack]
            matched_participants = []
            for entry in profile.enabled_watch_entries():
                if entry.matches_text(haystack) or entry.display_name in claim.participants:
                    matched_participants.append(entry.display_name)

            topic_matches = [claim.topic] if claim.topic and claim.topic.lower() in {i.lower() for i in profile.interests} else []
            semantic_scores = []
            for interest in profile.interests:
                semantic_scores.append(cosine_similarity(claim.embedding, embed_text(interest)))

            profile_origin_boost = 0.15 if claim.profile_id == profile.profile_id else 0.0
            interest_score = min(1.0, len(matched_interests) * 0.22)
            participant_score = min(1.0, len(matched_participants) * 0.28)
            semantic_score = max(semantic_scores) if semantic_scores else 0.0
            score = min(1.0, interest_score + participant_score + semantic_score * 0.35 + profile_origin_boost)

            explanation_parts = []
            if matched_interests:
                explanation_parts.append(f"Matched interests: {', '.join(matched_interests)}")
            if matched_participants:
                explanation_parts.append(f"Matched watch list: {', '.join(matched_participants)}")
            if profile_origin_boost:
                explanation_parts.append(f"Collected under {profile.name} profile")
            if not explanation_parts:
                explanation_parts.append("No strong profile signal detected")

            results.append(RelevanceResult(
                profile_id=profile.profile_id,
                profile_name=profile.name,
                score=round(score, 3),
                matched_interests=matched_interests,
                matched_participants=matched_participants,
                matched_topics=topic_matches,
                explanation="; ".join(explanation_parts),
            ))

        return sorted(results, key=lambda item: item.score, reverse=True)