"""Intelligence collection layer for profile-driven corpus acquisition."""

from .collector import IntelligenceCollector
from .config import load_profiles, save_profiles
from .corpus import CorpusManager
from .analyst import PersonalIntelligenceAnalyst, Phase4PipelineResult, run_phase4_pipeline
from .briefing import BriefItem, MorningBrief, MorningBriefGenerator, generate_morning_brief_markdown
from .claims import ClaimExtractor, IntelligenceClaim
from .correlation import CrossSourceCluster, CrossSourceIntelligenceEngine
from .deep_dive import InteractiveDeepDive, InteractiveDeepDiveGenerator
from .dedupe import DeduplicationStore
from .discovery import DiscoveryEngine
from .importance import ImportanceEngine, ImportanceResult
from .models import (
    CollectionJob,
    DiscoveredEpisode,
    InformationEvent,
    InformationEventType,
    IntelligenceProfile,
    PodcastSource,
    SourceGraph,
    WatchListEntry,
)
from .novelty import NoveltyEngine, NoveltyResult
from .corpus_audit import audit_corpus, generate_corpus_audit_markdown
from .discoverers import DiscovererRegistry, InformationEventDiscoverer, PodcastDiscoverer
from .playbook import generate_source_playbook
from .relevance import RelevanceEngine, RelevanceResult
from .route_confidence import RouteConfidenceEngine
from .route_registry import AcquisitionRouteRegistry, AcquisitionRoute, RouteSelection
from .registry_evolution import RegistryEvolutionEngine
from .recertification import RouteRecertificationService
from .scheduler import RuntimeScheduler
from .state import FileStateStore

__all__ = [
    "AcquisitionRoute",
    "AcquisitionRouteRegistry",
    "BriefItem",
    "ClaimExtractor",
    "CollectionJob",
    "CorpusManager",
    "CrossSourceCluster",
    "CrossSourceIntelligenceEngine",
    "DeduplicationStore",
    "DiscoveredEpisode",
    "DiscoveryEngine",
    "FileStateStore",
    "ImportanceEngine",
    "ImportanceResult",
    "InformationEvent",
    "InformationEventType",
    "IntelligenceClaim",
    "IntelligenceCollector",
    "IntelligenceProfile",
    "InteractiveDeepDive",
    "InteractiveDeepDiveGenerator",
    "MorningBrief",
    "MorningBriefGenerator",
    "NoveltyEngine",
    "NoveltyResult",
    "PersonalIntelligenceAnalyst",
    "Phase4PipelineResult",
    "PodcastSource",
    "RelevanceEngine",
    "RelevanceResult",
    "RouteSelection",
    "RouteConfidenceEngine",
    "RouteRecertificationService",
    "RegistryEvolutionEngine",
    "DiscovererRegistry",
    "InformationEventDiscoverer",
    "PodcastDiscoverer",
    "RuntimeScheduler",
    "audit_corpus",
    "generate_morning_brief_markdown",
    "generate_corpus_audit_markdown",
    "generate_source_playbook",
    "run_phase4_pipeline",
    "SourceGraph",
    "WatchListEntry",
    "inspect_intelligence_runtime",
    "load_profiles",
    "save_profiles",
]


def __getattr__(name: str):
    if name == "inspect_intelligence_runtime":
        from .inspector import inspect_intelligence_runtime
        return inspect_intelligence_runtime
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
