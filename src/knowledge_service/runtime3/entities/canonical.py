"""Canonical entity aliases and type hints."""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from ..models import EntityType


CANONICAL_ALIASES: Dict[str, Tuple[str, EntityType]] = {
    "openai": ("OpenAI", EntityType.COMPANY),
    "anthropic": ("Anthropic", EntityType.COMPANY),
    "google": ("Google", EntityType.COMPANY),
    "meta": ("Meta", EntityType.COMPANY),
    "microsoft": ("Microsoft", EntityType.COMPANY),
    "apple": ("Apple", EntityType.COMPANY),
    "amazon": ("Amazon", EntityType.COMPANY),
    "nvidia": ("Nvidia", EntityType.COMPANY),
    "huawei": ("Huawei", EntityType.COMPANY),
    "bytedance": ("ByteDance", EntityType.COMPANY),
    "xai": ("xAI", EntityType.COMPANY),
    "mercury": ("Mercury", EntityType.COMPANY),
    "constantine": ("Constantine", EntityType.PERSON),
    "eric swalwell": ("Eric Swalwell", EntityType.PERSON),
    "katie porter": ("Katie Porter", EntityType.PERSON),
    "xavier becerra": ("Xavier Becerra", EntityType.PERSON),
    "nate silver": ("Nate Silver", EntityType.PERSON),
    "gavin newsom": ("Gavin Newsom", EntityType.PERSON),
    "grant sanderson": ("Grant Sanderson", EntityType.PERSON),
    "byzantine empire": ("Byzantine Empire", EntityType.PLACE),
    "east roman empire": ("East Roman Empire", EntityType.PLACE),
    "roman empire": ("Roman Empire", EntityType.PLACE),
    "california": ("California", EntityType.PLACE),
    "dark matter": ("Dark Matter", EntityType.TOPIC),
    "glm-5": ("GLM-5", EntityType.PRODUCT),
    "glm5": ("GLM-5", EntityType.PRODUCT),
    "chatgpt": ("ChatGPT", EntityType.PRODUCT),
    "gpt-4": ("GPT-4", EntityType.PRODUCT),
    "rlvr": ("RLVR", EntityType.TECHNOLOGY),
    "coding agents": ("Coding Agents", EntityType.TECHNOLOGY),
    "enterprise ai": ("Enterprise AI", EntityType.TECHNOLOGY),
    "ai agents": ("AI Agents", EntityType.TECHNOLOGY),
    "hard fork": ("Hard Fork", EntityType.PUBLICATION),
    "new york times": ("New York Times", EntityType.PUBLICATION),
    "lex fridman": ("Lex Fridman", EntityType.PERSON),
    "dwarkesh": ("Dwarkesh Patel", EntityType.PERSON),
    "all-in podcast": ("All-In Podcast", EntityType.PUBLICATION),
    "all in podcast": ("All-In Podcast", EntityType.PUBLICATION),
    "all-in podcast": ("All-In Podcast", EntityType.PUBLICATION),
    "google": ("Google", EntityType.COMPANY),
    "gemini": ("Gemini", EntityType.PRODUCT),
    "democrats": ("Democratic Party", EntityType.ORGANIZATION),
    "republicans": ("Republican Party", EntityType.ORGANIZATION),
    "california": ("California", EntityType.PLACE),
    "stanford": ("Stanford University", EntityType.ORGANIZATION),
    "mit": ("MIT", EntityType.ORGANIZATION),
    "openai": ("OpenAI", EntityType.COMPANY),
    "deepmind": ("DeepMind", EntityType.COMPANY),
    "white house": ("White House", EntityType.ORGANIZATION),
    "congress": ("U.S. Congress", EntityType.ORGANIZATION),
    "supreme court": ("U.S. Supreme Court", EntityType.ORGANIZATION),
    "new york times": ("New York Times", EntityType.PUBLICATION),
    "hard fork": ("Hard Fork", EntityType.PUBLICATION),
    "dwarkesh podcast": ("Dwarkesh Podcast", EntityType.PUBLICATION),
    "lex fridman podcast": ("Lex Fridman Podcast", EntityType.PUBLICATION),
}

ORG_SUFFIXES = (" Inc", " Corp", " LLC", " Ltd", " AI", " Labs", " Technologies")
TECH_PATTERNS = ("AI", "GPT", "LLM", "API", "SDK", "ML", "GPU", "CPU", "RLVR", "GLM")


def resolve_canonical(name: str) -> Optional[Tuple[str, EntityType]]:
    key = name.strip().lower()
    if key in CANONICAL_ALIASES:
        return CANONICAL_ALIASES[key]
    for alias, value in CANONICAL_ALIASES.items():
        if alias in key or key in alias:
            return value
    return None


def infer_entity_type(name: str) -> EntityType:
    canonical = resolve_canonical(name)
    if canonical:
        return canonical[1]
    if any(suffix in name for suffix in ORG_SUFFIXES):
        return EntityType.ORGANIZATION
    if any(pattern in name.upper() for pattern in TECH_PATTERNS):
        return EntityType.TECHNOLOGY
    if len(name.split()) == 1 and name[0].isupper():
        return EntityType.TOPIC
    if len(name.split()) >= 2 and name[0].isupper():
        return EntityType.PERSON
    return EntityType.TOPIC