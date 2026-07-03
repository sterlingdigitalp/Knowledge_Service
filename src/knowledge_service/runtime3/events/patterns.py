"""Event detection patterns."""

from __future__ import annotations

import re
from typing import List, Tuple

from ..models import EventType

EVENT_RULES: List[Tuple[EventType, re.Pattern, str]] = [
    (EventType.LAUNCH, re.compile(r"\b(?:launch(?:ed|es|ing)?|unveil(?:ed|s)?|debut(?:ed)?)\b", re.I), "launch"),
    (EventType.ACQUISITION, re.compile(r"\b(?:acquir(?:ed|es|ing)|bought|merger|merged)\b", re.I), "acquisition"),
    (EventType.FUNDING, re.compile(r"\b(?:raised|raising|funding\s+round|series\s+[a-e]|seed\s+round)\b", re.I), "funding"),
    (EventType.RESEARCH_PAPER, re.compile(r"\b(?:research\s+paper|published\s+(?:a\s+)?study|peer[- ]reviewed)\b", re.I), "research"),
    (EventType.POLICY, re.compile(r"\b(?:policy|regulation|legislation|bill|executive\s+order)\b", re.I), "policy"),
    (EventType.HIRING, re.compile(r"\b(?:hired|hiring|appointed|joins\s+as|new\s+ceo|new\s+cto)\b", re.I), "hiring"),
    (EventType.PARTNERSHIP, re.compile(r"\b(?:partner(?:ed|ship)|collaborat(?:ed|ion)|alliance)\b", re.I), "partnership"),
    (EventType.RELEASE, re.compile(r"\b(?:released?|shipping|rollout|available\s+now)\b", re.I), "release"),
    (EventType.SCIENTIFIC_DISCOVERY, re.compile(r"\b(?:discovered|discovery|detected|observed|found\s+evidence)\b", re.I), "discovery"),
    (EventType.LEGAL_ACTION, re.compile(r"\b(?:lawsuit|sued|indicted|antitrust|court\s+ruling)\b", re.I), "legal"),
    (EventType.SPEECH, re.compile(r"\b(?:speech|addressed|testified|remarks)\b", re.I), "speech"),
    (EventType.INTERVIEW, re.compile(r"\b(?:interview(?:ed)?|sat\s+down\s+with|chatted\s+with)\b", re.I), "interview"),
    (EventType.DEBATE, re.compile(r"\b(?:debate|argued|disagree|controversy|dispute)\b", re.I), "debate"),
    (EventType.PRODUCT_ANNOUNCEMENT, re.compile(r"\b(?:announced|introducing|new\s+(?:product|feature|model|chip))\b", re.I), "product"),
    (EventType.ELECTION, re.compile(r"\b(?:election|race|ballot|polls?|primary|caucus|attorney\s+general)\b", re.I), "election"),
]