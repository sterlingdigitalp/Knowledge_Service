"""Pattern libraries for transcript segment classification."""

from __future__ import annotations

import re
from typing import List, Tuple

from ..models import SegmentType


SPONSOR_PATTERNS: List[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bthanks?\s+to\s+our\s+(?:partner|sponsor)",
        r"\bthis\s+(?:episode|podcast|show)\s+is\s+(?:brought|sponsored)\s+to\s+you",
        r"\bsponsored\s+by\b",
        r"\bvisit\s+[a-z0-9]+\.(?:com|io|ai|co)\b",
        r"\bgo\s+to\s+[a-z0-9]+\.(?:com|io|ai|co)\b",
        r"\buse\s+code\s+[A-Z0-9]+\b",
        r"\bpromo\s+code\b",
        r"\bmercury\.com\b",
        r"\bnorthwestregisteredagent\b",
        r"\bplaud\.ai\b",
        r"\bamzn\.to/\b",
        r"\bslash\s+command\b",
        r"\bcheck\s+out\s+(?:our\s+)?(?:partner|sponsor)",
        r"\bstarting\s+a\s+business\?\b",
    ]
]

INTRO_PATTERNS: List[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"^welcome\s+to\s+(?:the\s+)?",
        r"^today\s+(?:on|in)\s+(?:the\s+)?",
        r"^this\s+is\s+(?:the\s+)?",
        r"^i(?:'m|\s+am)\s+(?:your\s+)?host\b",
        r"^joining\s+(?:us|me)\s+today\b",
        r"^intro\s+music\b",
        r"^intro\s+video\b",
        r"\bjoins\s+the\s+pod\b",
        r"\bfollow\s+(?:us|me|the)\s+on\s+(?:x|twitter|instagram|tiktok|linkedin)\b",
        r"\bfollow\s+nate\b",
        r"\bfollow\s+the\s+besties\b",
    ]
]

OUTRO_PATTERNS: List[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bthanks?\s+for\s+(?:listening|watching|tuning\s+in)\b",
        r"\bsee\s+you\s+next\s+(?:time|week|episode)\b",
        r"\bsubscribe\s+(?:to|on)\b",
        r"\bleave\s+(?:us\s+)?a\s+review\b",
        r"\brate\s+and\s+review\b",
        r"\bif\s+you\s+enjoyed\s+this\b",
        r"\buntil\s+next\s+time\b",
    ]
]

META_REQUEST_PATTERNS: List[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bif\s+you\s+want\s+to\s+help\s+me\s+out\b",
        r"\bhelp\s+me\s+figure\s+out\s+where\b",
        r"\bsubscribe\s+to\s+(?:my\s+)?(?:youtube|channel)\b",
        r"\bhit\s+(?:the\s+)?(?:like|subscribe)\s+button\b",
        r"\blet\s+me\s+know\s+(?:in\s+the\s+comments|what\s+you\s+think)\b",
        r"\bshare\s+this\s+(?:episode|video)\b",
    ]
]

HOUSEKEEPING_PATTERNS: List[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bwe(?:'ll|\s+will)\s+be\s+right\s+back\b",
        r"\bquick\s+break\b",
        r"\bafter\s+the\s+break\b",
        r"\btechnical\s+difficulties\b",
    ]
]

QA_PATTERNS: List[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"^(?:so\s+)?(?:my\s+)?(?:first\s+)?question\s+(?:is|for\s+you)\b",
        r"^what\s+(?:do\s+you|would\s+you)\s+think\b",
        r"^can\s+you\s+(?:tell|explain|walk)\b",
        r"^how\s+(?:do|did|would)\s+you\b",
    ]
]

INTERVIEW_PATTERNS: List[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\btoday\s+i(?:'m|\s+am)\s+chatting\s+with\b",
        r"\bjoined\s+by\b",
        r"\bsitting\s+down\s+with\b",
        r"\binterview\s+with\b",
    ]
]

NEWS_PATTERNS: List[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bannounced\b",
        r"\blaunch(?:ed|es)?\b",
        r"\bacquired\b",
        r"\braised\s+\$?\d",
        r"\belection\b",
        r"\bpolicy\b",
        r"\bresearch\s+(?:paper|shows|finds)\b",
        r"\bscientists?\s+(?:discovered|found)\b",
        r"\baccording\s+to\b",
        r"\breport(?:s|ed)?\s+that\b",
    ]
]


def score_patterns(text: str, patterns: List[re.Pattern]) -> int:
    return sum(1 for pattern in patterns if pattern.search(text))


def classify_segment_text(text: str, *, position_ratio: float = 0.5) -> Tuple[SegmentType, float]:
    """Classify a transcript segment by content and position in episode."""
    normalized = " ".join((text or "").split())
    if not normalized or len(normalized) < 12:
        return SegmentType.UNKNOWN, 0.3

    scores = {
        SegmentType.SPONSOR: score_patterns(normalized, SPONSOR_PATTERNS) * 2.0,
        SegmentType.ADVERTISEMENT: score_patterns(normalized, SPONSOR_PATTERNS) * 1.5,
        SegmentType.INTRO: score_patterns(normalized, INTRO_PATTERNS) * 1.8,
        SegmentType.OUTRO: score_patterns(normalized, OUTRO_PATTERNS) * 1.8,
        SegmentType.META_REQUEST: score_patterns(normalized, META_REQUEST_PATTERNS) * 2.0,
        SegmentType.HOUSEKEEPING: score_patterns(normalized, HOUSEKEEPING_PATTERNS) * 1.5,
        SegmentType.QA: score_patterns(normalized, QA_PATTERNS) * 1.2,
        SegmentType.INTERVIEW: score_patterns(normalized, INTERVIEW_PATTERNS) * 1.0,
        SegmentType.NEWS: score_patterns(normalized, NEWS_PATTERNS) * 1.0,
    }

    # Position heuristics: first/last 5% of episode often intro/outro/sponsor
    if position_ratio < 0.05:
        scores[SegmentType.INTRO] += 1.5
        scores[SegmentType.SPONSOR] += 1.0
    if position_ratio > 0.92 and score_patterns(normalized, OUTRO_PATTERNS) > 0:
        scores[SegmentType.OUTRO] += 1.5
        scores[SegmentType.SPONSOR] += 0.8
        scores[SegmentType.META_REQUEST] += 1.0

    # Long sponsor blocks with URLs
    if len(normalized) > 200 and re.search(r"https?://|\.com/|\.ai/", normalized, re.I):
        scores[SegmentType.SPONSOR] += 2.0

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    news_score = scores[SegmentType.NEWS]
    if news_score >= 1.0 and news_score >= best_score * 0.8:
        return SegmentType.NEWS, min(0.98, 0.60 + news_score * 0.06)

    if best_score < 1.0:
        if "?" in normalized[:80]:
            return SegmentType.QA, 0.55
        if position_ratio < 0.15 and len(normalized) < 300:
            return SegmentType.INTRO, 0.5
        return SegmentType.DISCUSSION, 0.55

    # Substantive content in final segments should not default to outro
    if best_type in {SegmentType.OUTRO, SegmentType.META_REQUEST} and news_score >= 0.5:
        return SegmentType.DISCUSSION, min(0.90, 0.55 + news_score * 0.08)

    confidence = min(0.98, 0.55 + best_score * 0.08)
    return best_type, round(confidence, 3)