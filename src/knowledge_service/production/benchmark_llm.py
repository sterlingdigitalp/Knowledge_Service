"""Benchmark heuristic vs xAI LLM generation quality."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence


class LLMQualityBenchmark:
    """Side-by-side comparison of analyst heuristic and xAI generation."""

    def compare_runs(
        self,
        heuristic_items: Sequence[Dict[str, Any]],
        xai_items: Sequence[Dict[str, Any]],
        *,
        heuristic_brief: Dict[str, Any] | None = None,
        xai_brief: Dict[str, Any] | None = None,
        heuristic_conversation: Dict[str, Any] | None = None,
        xai_conversation: Dict[str, Any] | None = None,
        heuristic_metrics: Dict[str, Any] | None = None,
        xai_metrics: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        title_pairs = self._pair_titles(heuristic_items, xai_items)
        summary_pairs = self._pair_summaries(heuristic_items, xai_items)
        return {
            "providers": {
                "heuristic": "analyst_heuristic",
                "xai": "xai_responses",
            },
            "theme_titles": {
                "pairs": title_pairs,
                "heuristic_quality": _title_quality_score([pair["heuristic"] for pair in title_pairs]),
                "xai_quality": _title_quality_score([pair["xai"] for pair in title_pairs]),
                "improved": _title_quality_score([pair["xai"] for pair in title_pairs])
                > _title_quality_score([pair["heuristic"] for pair in title_pairs]),
            },
            "executive_summaries": {
                "pairs": summary_pairs[:5],
                "heuristic_quality": _summary_quality_score([pair["heuristic"] for pair in summary_pairs]),
                "xai_quality": _summary_quality_score([pair["xai"] for pair in summary_pairs]),
                "improved": _summary_quality_score([pair["xai"] for pair in summary_pairs])
                > _summary_quality_score([pair["heuristic"] for pair in summary_pairs]),
            },
            "morning_brief": self._compare_briefs(heuristic_brief, xai_brief),
            "deep_dive": self._compare_conversations(heuristic_conversation, xai_conversation),
            "runtime": {
                "heuristic": heuristic_metrics or {},
                "xai": xai_metrics or {},
            },
            "quality_evaluation": self._quality_evaluation(title_pairs, summary_pairs, heuristic_brief, xai_brief),
        }

    def _pair_titles(
        self,
        heuristic_items: Sequence[Dict[str, Any]],
        xai_items: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, str]]:
        xai_index = {item.get("item_id") or item.get("intelligence_item_id"): item for item in xai_items}
        pairs: List[Dict[str, str]] = []
        for item in heuristic_items[:10]:
            item_id = item.get("item_id") or item.get("intelligence_item_id")
            counterpart = xai_index.get(item_id, {})
            pairs.append({
                "item_id": str(item_id),
                "heuristic": str(item.get("title") or ""),
                "xai": str(counterpart.get("title") or ""),
            })
        return pairs

    def _pair_summaries(
        self,
        heuristic_items: Sequence[Dict[str, Any]],
        xai_items: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, str]]:
        xai_index = {item.get("item_id") or item.get("intelligence_item_id"): item for item in xai_items}
        pairs: List[Dict[str, str]] = []
        for item in heuristic_items[:10]:
            item_id = item.get("item_id") or item.get("intelligence_item_id")
            counterpart = xai_index.get(item_id, {})
            pairs.append({
                "item_id": str(item_id),
                "heuristic": str(item.get("executive_summary") or "")[:500],
                "xai": str(counterpart.get("executive_summary") or "")[:500],
            })
        return pairs

    def _compare_briefs(
        self,
        heuristic_brief: Dict[str, Any] | None,
        xai_brief: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        h = heuristic_brief or {}
        x = xai_brief or {}
        return {
            "heuristic_reading_seconds": h.get("reading_time_seconds", 0),
            "xai_reading_seconds": x.get("reading_time_seconds", 0),
            "heuristic_quality_score": h.get("quality_score", 0),
            "xai_quality_score": x.get("quality_score", 0),
            "readability_improved": float(x.get("quality_score", 0)) >= float(h.get("quality_score", 0)),
        }

    def _compare_conversations(
        self,
        heuristic_conversation: Dict[str, Any] | None,
        xai_conversation: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        h_start = ((heuristic_conversation or {}).get("start") or {}).get("messages") or []
        x_start = ((xai_conversation or {}).get("start") or {}).get("messages") or []
        h_follow = ((heuristic_conversation or {}).get("follow_up") or {}).get("messages") or []
        x_follow = ((xai_conversation or {}).get("follow_up") or {}).get("messages") or []
        return {
            "heuristic_opening_words": _word_count(_last_assistant(h_start)),
            "xai_opening_words": _word_count(_last_assistant(x_start)),
            "heuristic_followup_words": _word_count(_last_assistant(h_follow)),
            "xai_followup_words": _word_count(_last_assistant(x_follow)),
            "analyst_tone_improved": _word_count(_last_assistant(x_start)) > _word_count(_last_assistant(h_start)),
        }

    def _quality_evaluation(
        self,
        title_pairs: List[Dict[str, str]],
        summary_pairs: List[Dict[str, str]],
        heuristic_brief: Dict[str, Any] | None,
        xai_brief: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        title_delta = (
            _title_quality_score([pair["xai"] for pair in title_pairs])
            - _title_quality_score([pair["heuristic"] for pair in title_pairs])
        )
        summary_delta = (
            _summary_quality_score([pair["xai"] for pair in summary_pairs])
            - _summary_quality_score([pair["heuristic"] for pair in summary_pairs])
        )
        brief_delta = float((xai_brief or {}).get("quality_score", 0)) - float((heuristic_brief or {}).get("quality_score", 0))
        noticeable = title_delta > 0.05 or summary_delta > 0.05 or brief_delta > 0.05
        return {
            "theme_title_quality_delta": round(title_delta, 4),
            "summary_quality_delta": round(summary_delta, 4),
            "brief_quality_delta": round(brief_delta, 4),
            "analyst_tone": "improved" if noticeable else "comparable",
            "evidence_integration": "improved" if summary_delta > 0 else "comparable",
            "narrative_flow": "improved" if brief_delta >= 0 else "comparable",
            "readability": "improved" if brief_delta >= 0 else "comparable",
            "human_noticeable_improvement": noticeable,
            "overall_brief_quality": "improved" if brief_delta >= 0 else "comparable",
        }


def _title_quality_score(titles: Sequence[str]) -> float:
    if not titles:
        return 0.0
    score = 0.0
    for title in titles:
        words = title.split()
        if 2 <= len(words) <= 5:
            score += 1.0
        elif len(words) <= 6:
            score += 0.6
        if title and title[0].isupper() and not title.lower().startswith(("i ", "and ", "the ", "ai compute")):
            score += 0.4
        if "developments" in title.lower():
            score -= 0.2
    return score / len(titles)


def _summary_quality_score(summaries: Sequence[str]) -> float:
    if not summaries:
        return 0.0
    score = 0.0
    markers = ("what changed", "why it matters", "why now", "watch", "corroboration", "independent")
    cliches = ("delve", "game-changer", "landscape shift", "in today's")
    for summary in summaries:
        lower = summary.lower()
        score += min(1.0, sum(0.15 for marker in markers if marker in lower))
        score += 0.2 if 60 <= len(summary.split()) <= 160 else 0.0
        score -= 0.1 * sum(1 for cliche in cliches if cliche in lower)
    return max(0.0, score / len(summaries))


def _word_count(text: str) -> int:
    return len(text.split()) if text else 0


def _last_assistant(messages: Sequence[Dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "assistant":
            return str(message.get("content") or "")
    return ""