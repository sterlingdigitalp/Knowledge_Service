"""Data models for profile-driven intelligence collection."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional
import hashlib
import re


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def stable_id(*parts: Any) -> str:
    raw = "|".join(_normal_hash_part(part) for part in parts if part is not None)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def content_hash(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def slugify(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", (value or "").strip().lower())
    return text.strip("-") or "unnamed"


def _normal_hash_part(part: Any) -> str:
    if isinstance(part, str):
        return " ".join(part.strip().lower().split())
    return str(part)


class PodcastListKind(str, Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    IGNORE = "ignore"


class InformationEventType(str, Enum):
    PODCAST_EPISODE = "podcast_episode"
    CONFERENCE_KEYNOTE = "conference_keynote"
    INTERVIEW = "interview"
    LIVESTREAM = "livestream"
    PANEL_DISCUSSION = "panel_discussion"
    AMA = "ama"
    EARNINGS_CALL = "earnings_call"
    RESEARCH_PRESENTATION = "research_presentation"
    UNIVERSITY_LECTURE = "university_lecture"
    PRODUCT_LAUNCH = "product_launch"
    CONGRESSIONAL_TESTIMONY = "congressional_testimony"
    FIRESIDE_CHAT = "fireside_chat"


class EpisodeStatus(str, Enum):
    DISCOVERED = "discovered"
    QUEUED = "queued"
    PROCESSED = "processed"
    SKIPPED = "skipped"
    FAILED = "failed"
    DUPLICATE = "duplicate"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


@dataclass
class WatchListEntry:
    display_name: str
    aliases: List[str] = field(default_factory=list)
    organization: Optional[str] = None
    source_handles: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    priority: int = 5
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def entry_id(self) -> str:
        return slugify(self.display_name)

    def names(self) -> List[str]:
        names = [self.display_name, *self.aliases]
        return [name for name in names if name]

    def matches_text(self, text: str) -> bool:
        if not self.enabled:
            return False
        haystack = f" {text.lower()} "
        for name in self.names():
            needle = f" {name.lower()} "
            if needle in haystack:
                return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "display_name": self.display_name,
            "aliases": list(self.aliases),
            "organization": self.organization,
            "source_handles": dict(self.source_handles),
            "enabled": self.enabled,
            "priority": self.priority,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WatchListEntry":
        return cls(
            display_name=str(data.get("display_name") or data.get("name") or ""),
            aliases=list(data.get("aliases") or []),
            organization=data.get("organization"),
            source_handles=dict(data.get("source_handles") or data.get("handles") or {}),
            enabled=bool(data.get("enabled", True)),
            priority=int(data.get("priority", 5)),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class PodcastSource:
    name: str
    url: str
    kind: PodcastListKind = PodcastListKind.OPTIONAL
    enabled: bool = True
    priority: int = 5
    polling_interval_seconds: int = 3600
    discovery_mode: str = "podscripts"
    transcript_source: str = "published"
    max_episodes: int = 5
    episode_urls: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def podcast_id(self) -> str:
        return stable_id(self.name, self.url)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "url": self.url,
            "kind": self.kind.value,
            "enabled": self.enabled,
            "priority": self.priority,
            "polling_interval_seconds": self.polling_interval_seconds,
            "discovery_mode": self.discovery_mode,
            "transcript_source": self.transcript_source,
            "max_episodes": self.max_episodes,
            "episode_urls": list(self.episode_urls),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], kind: Optional[str] = None) -> "PodcastSource":
        return cls(
            name=str(data.get("name") or data.get("title") or ""),
            url=str(data.get("url") or data.get("index_url") or data.get("feed_url") or ""),
            kind=PodcastListKind(kind or data.get("kind") or PodcastListKind.OPTIONAL.value),
            enabled=bool(data.get("enabled", True)),
            priority=int(data.get("priority", 5)),
            polling_interval_seconds=int(data.get("polling_interval_seconds", data.get("poll_interval_seconds", 3600))),
            discovery_mode=str(data.get("discovery_mode") or "podscripts"),
            transcript_source=str(data.get("transcript_source") or "published"),
            max_episodes=int(data.get("max_episodes", 5)),
            episode_urls=list(data.get("episode_urls") or []),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class IntelligenceProfile:
    name: str
    description: str = ""
    profile_id: str = ""
    icon: Optional[str] = None
    color: Optional[str] = None
    enabled: bool = True
    interests: List[str] = field(default_factory=list)
    watch_list: List[WatchListEntry] = field(default_factory=list)
    required_podcasts: List[PodcastSource] = field(default_factory=list)
    optional_podcasts: List[PodcastSource] = field(default_factory=list)
    ignore_podcasts: List[PodcastSource] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def __post_init__(self) -> None:
        if not self.profile_id:
            self.profile_id = slugify(self.name)

    def enabled_watch_entries(self) -> List[WatchListEntry]:
        return [entry for entry in self.watch_list if entry.enabled]

    def enabled_podcasts(self) -> List[PodcastSource]:
        podcasts = [*self.required_podcasts, *self.optional_podcasts]
        ignored_names = {podcast.name.lower() for podcast in self.ignore_podcasts if podcast.enabled}
        ignored_urls = {podcast.url for podcast in self.ignore_podcasts if podcast.enabled}
        return [
            podcast for podcast in podcasts
            if podcast.enabled and podcast.name.lower() not in ignored_names and podcast.url not in ignored_urls
        ]

    def matches_episode(self, text: str) -> tuple[List[str], List[str]]:
        watch_matches = [entry.display_name for entry in self.enabled_watch_entries() if entry.matches_text(text)]
        lower_text = text.lower()
        interest_matches = [interest for interest in self.interests if interest.lower() in lower_text]
        return watch_matches, interest_matches

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "color": self.color,
            "enabled": self.enabled,
            "interests": list(self.interests),
            "watch_list": [entry.to_dict() for entry in self.watch_list],
            "podcasts": {
                "required": [podcast.to_dict() for podcast in self.required_podcasts],
                "optional": [podcast.to_dict() for podcast in self.optional_podcasts],
                "ignore": [podcast.to_dict() for podcast in self.ignore_podcasts],
            },
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IntelligenceProfile":
        podcasts = data.get("podcasts") or {}
        return cls(
            profile_id=str(data.get("profile_id") or data.get("id") or ""),
            name=str(data.get("name") or ""),
            description=str(data.get("description") or ""),
            icon=data.get("icon"),
            color=data.get("color"),
            enabled=bool(data.get("enabled", True)),
            interests=list(data.get("interests") or []),
            watch_list=[WatchListEntry.from_dict(item) for item in data.get("watch_list", [])],
            required_podcasts=[PodcastSource.from_dict(item, "required") for item in podcasts.get("required", data.get("required_podcasts", []))],
            optional_podcasts=[PodcastSource.from_dict(item, "optional") for item in podcasts.get("optional", data.get("optional_podcasts", []))],
            ignore_podcasts=[PodcastSource.from_dict(item, "ignore") for item in podcasts.get("ignore", data.get("ignore_podcasts", []))],
            metadata=dict(data.get("metadata") or {}),
            created_at=str(data.get("created_at") or now_iso()),
            updated_at=str(data.get("updated_at") or now_iso()),
        )


@dataclass
class InformationEvent:
    """First-class monitored appearance of watched people in an information venue."""

    profile_id: str
    title: str
    url: str
    event_type: InformationEventType = InformationEventType.PODCAST_EPISODE
    venue: str = ""
    participants: List[str] = field(default_factory=list)
    source_id: str = ""
    event_id: str = ""
    event_date: Optional[str] = None
    description: str = ""
    source_url: str = ""
    matched_interests: List[str] = field(default_factory=list)
    priority: int = 5
    status: EpisodeStatus = EpisodeStatus.DISCOVERED
    discovered_at: str = field(default_factory=now_iso)
    processed_at: Optional[str] = None
    acquisition_hash: str = ""
    source_hash: str = ""
    transcript_hash: Optional[str] = None
    duplicate_of: Optional[str] = None
    knowledge_object_ids: List[str] = field(default_factory=list)
    acquisition_route: Optional[str] = None
    route_confidence: Optional[float] = None
    fallback_routes_attempted: List[str] = field(default_factory=list)
    route_selection_reason: List[str] = field(default_factory=list)
    transcript_provenance: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.event_id:
            self.event_id = stable_id(self.venue or "event", self.title, self.url)
        if not self.source_url:
            self.source_url = self.url
        if not self.source_hash:
            self.source_hash = content_hash(self.url)
        if not self.acquisition_hash:
            self.acquisition_hash = content_hash(f"{self.profile_id}|{self.url}")

    def relevance_score(self) -> int:
        return self.priority + (5 * len(self.participants)) + len(self.matched_interests)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "profile_id": self.profile_id,
            "event_type": self.event_type.value if isinstance(self.event_type, InformationEventType) else self.event_type,
            "venue": self.venue,
            "participants": list(self.participants),
            "source_id": self.source_id,
            "title": self.title,
            "url": self.url,
            "source_url": self.source_url,
            "event_date": self.event_date,
            "description": self.description,
            "matched_interests": list(self.matched_interests),
            "priority": self.priority,
            "status": self.status.value if isinstance(self.status, EpisodeStatus) else self.status,
            "discovered_at": self.discovered_at,
            "processed_at": self.processed_at,
            "acquisition_hash": self.acquisition_hash,
            "source_hash": self.source_hash,
            "transcript_hash": self.transcript_hash,
            "duplicate_of": self.duplicate_of,
            "knowledge_object_ids": list(self.knowledge_object_ids),
            "acquisition_route": self.acquisition_route,
            "route_confidence": self.route_confidence,
            "fallback_routes_attempted": list(self.fallback_routes_attempted),
            "route_selection_reason": list(self.route_selection_reason),
            "transcript_provenance": dict(self.transcript_provenance),
            "error": self.error,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InformationEvent":
        return cls(
            event_id=str(data.get("event_id") or data.get("episode_id") or ""),
            profile_id=str(data.get("profile_id") or ""),
            event_type=InformationEventType(data.get("event_type", InformationEventType.PODCAST_EPISODE.value)),
            venue=str(data.get("venue") or data.get("podcast_name") or ""),
            participants=list(data.get("participants") or data.get("matched_watch_entries") or []),
            source_id=str(data.get("source_id") or ""),
            title=str(data.get("title") or ""),
            url=str(data.get("url") or ""),
            source_url=str(data.get("source_url") or data.get("url") or ""),
            event_date=data.get("event_date") or data.get("episode_date"),
            description=str(data.get("description") or ""),
            matched_interests=list(data.get("matched_interests") or []),
            priority=int(data.get("priority", 5)),
            status=EpisodeStatus(data.get("status", EpisodeStatus.DISCOVERED.value)),
            discovered_at=str(data.get("discovered_at") or now_iso()),
            processed_at=data.get("processed_at"),
            acquisition_hash=str(data.get("acquisition_hash") or ""),
            source_hash=str(data.get("source_hash") or ""),
            transcript_hash=data.get("transcript_hash"),
            duplicate_of=data.get("duplicate_of"),
            knowledge_object_ids=list(data.get("knowledge_object_ids") or []),
            acquisition_route=data.get("acquisition_route"),
            route_confidence=data.get("route_confidence"),
            fallback_routes_attempted=list(data.get("fallback_routes_attempted") or []),
            route_selection_reason=list(data.get("route_selection_reason") or []),
            transcript_provenance=dict(data.get("transcript_provenance") or {}),
            error=data.get("error"),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class DiscoveredEpisode:
    profile_id: str
    podcast_name: str
    title: str
    url: str
    source_url: str
    episode_id: str = ""
    episode_date: Optional[str] = None
    description: str = ""
    matched_watch_entries: List[str] = field(default_factory=list)
    matched_interests: List[str] = field(default_factory=list)
    priority: int = 5
    status: EpisodeStatus = EpisodeStatus.DISCOVERED
    discovered_at: str = field(default_factory=now_iso)
    processed_at: Optional[str] = None
    acquisition_hash: str = ""
    source_hash: str = ""
    transcript_hash: Optional[str] = None
    duplicate_of: Optional[str] = None
    knowledge_object_ids: List[str] = field(default_factory=list)
    event_type: InformationEventType = InformationEventType.PODCAST_EPISODE
    source_id: str = ""
    acquisition_route: Optional[str] = None
    route_confidence: Optional[float] = None
    fallback_routes_attempted: List[str] = field(default_factory=list)
    route_selection_reason: List[str] = field(default_factory=list)
    transcript_provenance: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.episode_id:
            self.episode_id = stable_id(self.podcast_name, self.title, self.url)
        if not self.source_hash:
            self.source_hash = content_hash(self.url)
        if not self.acquisition_hash:
            self.acquisition_hash = content_hash(f"{self.profile_id}|{self.url}")

    def as_information_event(self) -> InformationEvent:
        return InformationEvent(
            event_id=self.episode_id,
            profile_id=self.profile_id,
            event_type=self.event_type,
            venue=self.podcast_name,
            participants=list(self.matched_watch_entries),
            source_id=self.source_id,
            title=self.title,
            url=self.url,
            source_url=self.source_url,
            event_date=self.episode_date,
            description=self.description,
            matched_interests=list(self.matched_interests),
            priority=self.priority,
            status=self.status,
            discovered_at=self.discovered_at,
            processed_at=self.processed_at,
            acquisition_hash=self.acquisition_hash,
            source_hash=self.source_hash,
            transcript_hash=self.transcript_hash,
            duplicate_of=self.duplicate_of,
            knowledge_object_ids=list(self.knowledge_object_ids),
            acquisition_route=self.acquisition_route,
            route_confidence=self.route_confidence,
            fallback_routes_attempted=list(self.fallback_routes_attempted),
            route_selection_reason=list(self.route_selection_reason),
            transcript_provenance=dict(self.transcript_provenance),
            error=self.error,
            metadata=dict(self.metadata),
        )

    @classmethod
    def from_information_event(cls, event: InformationEvent) -> "DiscoveredEpisode":
        return cls(
            episode_id=event.event_id,
            profile_id=event.profile_id,
            podcast_name=event.venue,
            title=event.title,
            url=event.url,
            source_url=event.source_url,
            episode_date=event.event_date,
            description=event.description,
            matched_watch_entries=list(event.participants),
            matched_interests=list(event.matched_interests),
            priority=event.priority,
            status=event.status,
            discovered_at=event.discovered_at,
            processed_at=event.processed_at,
            acquisition_hash=event.acquisition_hash,
            source_hash=event.source_hash,
            transcript_hash=event.transcript_hash,
            duplicate_of=event.duplicate_of,
            knowledge_object_ids=list(event.knowledge_object_ids),
            event_type=event.event_type,
            source_id=event.source_id,
            acquisition_route=event.acquisition_route,
            route_confidence=event.route_confidence,
            fallback_routes_attempted=list(event.fallback_routes_attempted),
            route_selection_reason=list(event.route_selection_reason),
            transcript_provenance=dict(event.transcript_provenance),
            error=event.error,
            metadata=dict(event.metadata),
        )

    def relevance_score(self) -> int:
        return self.priority + (5 * len(self.matched_watch_entries)) + len(self.matched_interests)

    def to_dict(self) -> Dict[str, Any]:
        payload = self.as_information_event().to_dict()
        payload.update({
            "episode_id": self.episode_id,
            "podcast_name": self.podcast_name,
            "episode_date": self.episode_date,
            "matched_watch_entries": list(self.matched_watch_entries),
        })
        return payload

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DiscoveredEpisode":
        event = InformationEvent.from_dict(data)
        episode = cls.from_information_event(event)
        episode.episode_id = str(data.get("episode_id") or event.event_id)
        episode.podcast_name = str(data.get("podcast_name") or event.venue)
        episode.episode_date = data.get("episode_date") or event.event_date
        episode.matched_watch_entries = list(data.get("matched_watch_entries") or event.participants)
        return episode


@dataclass
class SourceGraph:
    profile_id: str
    person: str
    aliases: List[str] = field(default_factory=list)
    organization: Optional[str] = None
    source_handles: Dict[str, str] = field(default_factory=dict)
    nodes: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    updated_at: str = field(default_factory=now_iso)

    def __post_init__(self) -> None:
        defaults = ["x", "podcast_appearances", "youtube", "company_blog", "conference_talks", "papers", "interviews"]
        for key in defaults:
            self.nodes.setdefault(key, [])

    @property
    def graph_id(self) -> str:
        return stable_id(self.profile_id, self.person)

    def record_appearance(self, episode: DiscoveredEpisode) -> None:
        event = episode.as_information_event()
        node_key = {
            InformationEventType.PODCAST_EPISODE.value: "podcast_appearances",
            InformationEventType.CONFERENCE_KEYNOTE.value: "conference_talks",
            InformationEventType.INTERVIEW.value: "interviews",
            InformationEventType.LIVESTREAM.value: "livestreams",
        }.get(event.event_type.value, "information_events")
        existing = {item.get("event_id") or item.get("episode_id") for item in self.nodes.setdefault(node_key, [])}
        event_id = event.event_id
        if event_id not in existing:
            self.nodes[node_key].append({
                "event_id": event_id,
                "episode_id": event_id,
                "event_type": event.event_type.value,
                "venue": event.venue,
                "podcast_name": event.venue,
                "title": event.title,
                "url": event.url,
                "event_date": event.event_date,
                "episode_date": event.event_date,
                "source_id": event.source_id,
                "acquisition_route": event.acquisition_route,
                "status": event.status.value if isinstance(event.status, EpisodeStatus) else event.status,
            })
        self.updated_at = now_iso()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "profile_id": self.profile_id,
            "person": self.person,
            "aliases": list(self.aliases),
            "organization": self.organization,
            "source_handles": dict(self.source_handles),
            "nodes": self.nodes,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_watch_entry(cls, profile_id: str, entry: WatchListEntry) -> "SourceGraph":
        graph = cls(
            profile_id=profile_id,
            person=entry.display_name,
            aliases=list(entry.aliases),
            organization=entry.organization,
            source_handles=dict(entry.source_handles),
        )
        for platform, handle in entry.source_handles.items():
            graph.nodes.setdefault(platform, []).append({"handle": handle, "status": "configured"})
        return graph

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourceGraph":
        return cls(
            profile_id=str(data.get("profile_id") or ""),
            person=str(data.get("person") or ""),
            aliases=list(data.get("aliases") or []),
            organization=data.get("organization"),
            source_handles=dict(data.get("source_handles") or {}),
            nodes=dict(data.get("nodes") or {}),
            updated_at=str(data.get("updated_at") or now_iso()),
        )


@dataclass
class CollectionJob:
    job_id: str
    mode: str
    status: JobStatus = JobStatus.QUEUED
    profile_ids: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    current_step: Optional[str] = None
    discovered_count: int = 0
    queued_count: int = 0
    processed_count: int = 0
    duplicate_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    errors: List[str] = field(default_factory=list)
    performance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "mode": self.mode,
            "status": self.status.value if isinstance(self.status, JobStatus) else self.status,
            "profile_ids": list(self.profile_ids),
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "current_step": self.current_step,
            "discovered_count": self.discovered_count,
            "queued_count": self.queued_count,
            "processed_count": self.processed_count,
            "duplicate_count": self.duplicate_count,
            "skipped_count": self.skipped_count,
            "failed_count": self.failed_count,
            "errors": list(self.errors),
            "performance": dict(self.performance),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CollectionJob":
        return cls(
            job_id=str(data.get("job_id") or ""),
            mode=str(data.get("mode") or "manual"),
            status=JobStatus(data.get("status", JobStatus.QUEUED.value)),
            profile_ids=list(data.get("profile_ids") or []),
            created_at=str(data.get("created_at") or now_iso()),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            current_step=data.get("current_step"),
            discovered_count=int(data.get("discovered_count", 0)),
            queued_count=int(data.get("queued_count", 0)),
            processed_count=int(data.get("processed_count", 0)),
            duplicate_count=int(data.get("duplicate_count", 0)),
            skipped_count=int(data.get("skipped_count", 0)),
            failed_count=int(data.get("failed_count", 0)),
            errors=list(data.get("errors") or []),
            performance=dict(data.get("performance") or {}),
        )


def profile_collection_to_dict(profiles: Iterable[IntelligenceProfile]) -> Dict[str, Any]:
    return {"profiles": [profile.to_dict() for profile in profiles]}
