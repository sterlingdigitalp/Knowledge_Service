"""Personal Intelligence Analyst — Phase 4/4.1 intelligence pipeline."""

from .models import Claim, MorningBrief, ScoredClaim
from .synthesis.models import IntelligenceBrief, IntelligenceItem

__all__ = [
    "IntelligenceAnalystPipeline",
    "Claim",
    "MorningBrief",
    "ScoredClaim",
    "IntelligenceItem",
    "IntelligenceBrief",
]


def __getattr__(name: str):
    if name == "IntelligenceAnalystPipeline":
        from .pipeline import IntelligenceAnalystPipeline
        return IntelligenceAnalystPipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")