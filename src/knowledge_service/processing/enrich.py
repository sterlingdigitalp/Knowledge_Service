"""Stage 6: Enrich — confidence computation, topic classification, evidence counting

Input: markdown content + chunks + extraction results
Output: enriched context with confidence, topics, evidence_count
"""

import re
from typing import Dict, Any, List, Optional
from .context import ProcessingContext, StageResult


DEFAULT_TOPIC_KEYWORDS: Dict[str, List[str]] = {
    "programming": ["function", "class", "api", "code", "software", "library", "framework",
                    "javascript", "python", "typescript", "react", "node", "algorithm"],
    "web_development": ["html", "css", "web", "browser", "frontend", "backend", "http",
                        "server", "client", "responsive", "rest", "graphql"],
    "data_science": ["data", "model", "statistics", "machine learning", "neural", "training",
                     "dataset", "regression", "classification", "analytics"],
    "devops": ["deployment", "infrastructure", "kubernetes", "docker", "container",
               "pipeline", "monitoring", "ci/cd", "cloud", "terraform"],
    "security": ["authentication", "encryption", "security", "vulnerability", "password",
                 "oauth", "token", "firewall", "audit", "permission"],
    "business": ["revenue", "market", "strategy", "investment", "growth", "customer",
                 "product", "pricing", "valuation", "acquisition"],
    "science": ["research", "study", "experiment", "methodology", "hypothesis", "analysis",
                "peer", "journal", "publication", "laboratory"],
    "documentation": ["documentation", "guide", "tutorial", "reference", "manual",
                      "installation", "configuration", "usage", "example", "quickstart"],
}


class EnrichStage:

    def execute(self, context: ProcessingContext, config: Dict[str, Any]) -> ProcessingContext:
        compute_conf = config.get("compute_confidence", True)
        classify_topics = config.get("classify_topics", True)

        markdown = context.markdown
        if not markdown:
            context.stage_results["enrich"] = StageResult("enrich", True, confidence_impact=-0.05, warnings=["No content to enrich"])
            return context

        if classify_topics:
            topics = self._classify_topics(markdown)
            context.topics = topics

        if compute_conf:
            confidence = self._compute_confidence(context, config)
            context.confidence = confidence

        evidence_count = self._count_evidence(context)
        context.evidence_count = evidence_count

        context.stage_results["enrich"] = StageResult("enrich", True, confidence_impact=0.0)
        return context

    def _classify_topics(self, content: str) -> List[str]:
        lower = content.lower()
        topics: List[str] = []
        for topic, keywords in DEFAULT_TOPIC_KEYWORDS.items():
            for kw in keywords:
                if kw in lower:
                    topics.append(topic)
                    break
        return topics[:5]

    def _compute_confidence(self, context: ProcessingContext, config: Dict[str, Any]) -> float:
        w1 = config.get("weight_source_trust", 0.35)
        w2 = config.get("weight_content_completeness", 0.25)
        w3 = config.get("weight_processing_quality", 0.25)
        w4 = config.get("weight_evidence_strength", 0.15)

        source_trust = self._compute_source_trust(context, config)
        content_completeness = self._compute_content_completeness(context)
        processing_quality = self._compute_processing_quality(context)
        evidence_strength = self._compute_evidence_strength(context)

        raw = w1 * source_trust + w2 * content_completeness + w3 * processing_quality + w4 * evidence_strength
        for adj in context.confidence_adjustments:
            raw += adj
        return max(0.0, min(1.0, raw))

    def _compute_source_trust(self, context: ProcessingContext, config: Dict[str, Any]) -> float:
        return config.get("default_source_trust", 0.7)

    def _compute_content_completeness(self, context: ProcessingContext) -> float:
        score = 0.0
        total = 8
        if context.title:
            score += 1
        if context.authors:
            score += 1
        if context.language and context.language != "unknown":
            score += 1
        if context.word_count > 0:
            score += 1
        if context.markdown:
            score += 1
        if context.extracted_data.get("published_date"):
            score += 1
        if context.citations:
            score += 1
        if context.raw_content_hash:
            score += 1
        return score / total

    def _compute_processing_quality(self, context: ProcessingContext) -> float:
        total_stages = 7
        successful = 0
        for sr in context.stage_results.values():
            if sr.success:
                successful += 1
        base = successful / total_stages
        for adj in context.confidence_adjustments:
            base += adj
        return max(0.0, min(1.0, base))

    def _compute_evidence_strength(self, context: ProcessingContext) -> float:
        evidence_count = 0
        if context.citations:
            evidence_count += len(context.citations)
        if context.bundle:
            if context.bundle.provider_executions:
                evidence_count += len(context.bundle.provider_executions)
            if context.bundle.acquired_documents:
                evidence_count += len(context.bundle.acquired_documents)
        if evidence_count == 0:
            return 0.1
        return min(1.0, evidence_count / 10.0)

    def _count_evidence(self, context: ProcessingContext) -> int:
        count = 0
        if context.citations:
            count += len(context.citations)
        if context.bundle:
            if context.bundle.provider_executions:
                count += len(context.bundle.provider_executions)
            if context.bundle.acquired_documents:
                count += len(context.bundle.acquired_documents)
        if count == 0:
            count = 1
        return count
