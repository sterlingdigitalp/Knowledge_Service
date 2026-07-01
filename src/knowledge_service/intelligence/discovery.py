"""Podcast and transcript-page discovery for Intelligence Profiles."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from html import unescape
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse
import re
import time

import httpx

from .dedupe import DeduplicationStore
from .models import DiscoveredEpisode, EpisodeStatus, InformationEventType, IntelligenceProfile, PodcastListKind, PodcastSource, now_iso, stable_id
from .route_registry import AcquisitionRouteRegistry
from .state import FileStateStore


@dataclass
class DiscoveryResult:
    profile_id: str
    podcast_name: str
    status: str
    found_count: int = 0
    queued_count: int = 0
    duplicate_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    episodes: List[DiscoveredEpisode] = field(default_factory=list)
    error: Optional[str] = None
    elapsed_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "podcast_name": self.podcast_name,
            "status": self.status,
            "found_count": self.found_count,
            "queued_count": self.queued_count,
            "duplicate_count": self.duplicate_count,
            "skipped_count": self.skipped_count,
            "failed_count": self.failed_count,
            "episodes": [episode.to_dict() for episode in self.episodes],
            "error": self.error,
            "elapsed_seconds": round(self.elapsed_seconds, 6),
        }


class DiscoveryEngine:
    """Discover information events via the discoverer registry."""

    def __init__(
        self,
        state: FileStateStore,
        dedupe: DeduplicationStore,
        route_registry: Optional[AcquisitionRouteRegistry] = None,
        timeout_seconds: float = 30.0,
        discoverer_registry: Optional[Any] = None,
    ):
        self.state = state
        self.dedupe = dedupe
        self.route_registry = route_registry
        self.timeout_seconds = timeout_seconds
        if discoverer_registry is None:
            from .discoverers.registry import DiscovererRegistry
            discoverer_registry = DiscovererRegistry()
        self.discoverer_registry = discoverer_registry

    def discover(self, profiles: List[IntelligenceProfile]) -> List[DiscoveryResult]:
        from .discoverers.base import DiscoveryContext

        context = DiscoveryContext(
            state=self.state,
            dedupe=self.dedupe,
            route_registry=self.route_registry,
            timeout_seconds=self.timeout_seconds,
        )
        return self.discoverer_registry.discover(profiles, context)

    def discover_for_person(self, profile: IntelligenceProfile, person_name: str) -> List[DiscoveryResult]:
        entry = next((item for item in profile.enabled_watch_entries() if item.display_name == person_name), None)
        if entry is None:
            return []
        return self.discover([profile])

    def discover_podcast(
        self,
        profile: IntelligenceProfile,
        podcast: PodcastSource,
        watched_people: Optional[List[Any]] = None,
    ) -> DiscoveryResult:
        started = time.perf_counter()
        result = DiscoveryResult(profile_id=profile.profile_id, podcast_name=podcast.name, status="success")
        try:
            candidates = self._episode_candidates(podcast)
            result.found_count = len(candidates)
            for candidate in candidates[: max(1, podcast.max_episodes)]:
                episode = self._episode_from_candidate(profile, podcast, candidate)
                watch_matches, interest_matches = profile.matches_episode(
                    " ".join([episode.title, episode.description, episode.url])
                )
                episode.matched_watch_entries = watch_matches
                episode.matched_interests = interest_matches
                if podcast.kind == PodcastListKind.OPTIONAL and not watch_matches and not interest_matches:
                    episode.status = EpisodeStatus.SKIPPED
                    episode.error = "No watched-person or interest match"
                    result.skipped_count += 1
                    result.episodes.append(episode)
                    continue
                should_queue, duplicate_key, duplicate_of = self.dedupe.should_queue(episode)
                if not should_queue:
                    episode.status = EpisodeStatus.DUPLICATE
                    episode.duplicate_of = duplicate_of
                    episode.error = f"Duplicate {duplicate_key}"
                    result.duplicate_count += 1
                else:
                    episode.status = EpisodeStatus.QUEUED
                    self.dedupe.register_discovery(episode)
                    result.queued_count += 1
                result.episodes.append(episode)
            self.dedupe.save()
        except Exception as exc:
            result.status = "failed"
            result.error = str(exc)
            result.failed_count += 1
        result.elapsed_seconds = time.perf_counter() - started
        return result

    def _episode_candidates(self, podcast: PodcastSource) -> List[Dict[str, Any]]:
        if podcast.episode_urls:
            return [
                {
                    "url": url,
                    "title": _title_from_url(url),
                    "description": "",
                    "episode_date": None,
                    "source_url": podcast.url,
                }
                for url in podcast.episode_urls
            ]
        if podcast.discovery_mode not in {"podscripts", "page", "html"}:
            raise ValueError(f"Unsupported discovery mode: {podcast.discovery_mode}")
        response = httpx.get(
            podcast.url,
            timeout=self.timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "Knowledge_Service/Phase3 Discovery"},
        )
        response.raise_for_status()
        candidates = _extract_episode_links(podcast.url, response.text)
        if not candidates:
            page_title = _extract_title(response.text) or _title_from_url(podcast.url)
            candidates = [{"url": podcast.url, "title": page_title, "description": _visible_text(response.text)[:1000], "episode_date": None, "source_url": podcast.url}]
        return candidates

    def _episode_from_candidate(self, profile: IntelligenceProfile, podcast: PodcastSource, candidate: Dict[str, Any]) -> DiscoveredEpisode:
        title = candidate.get("title") or _title_from_url(candidate["url"])
        episode_date = candidate.get("episode_date") or _extract_date(" ".join([title, candidate.get("description", "")]))
        source_id = ""
        if self.route_registry is not None:
            source_id = self.route_registry.resolve_source_id(podcast_name=podcast.name, url=candidate["url"])
        return DiscoveredEpisode(
            profile_id=profile.profile_id,
            podcast_name=podcast.name,
            title=title,
            url=candidate["url"],
            source_url=candidate.get("source_url") or podcast.url,
            episode_date=episode_date,
            description=candidate.get("description", ""),
            priority=podcast.priority,
            event_type=InformationEventType.PODCAST_EPISODE,
            source_id=source_id,
            metadata={
                "podcast_id": podcast.podcast_id,
                "podcast_kind": podcast.kind.value,
                "discovery_mode": podcast.discovery_mode,
                "transcript_source": podcast.transcript_source,
                "discovery_strategy": "person_centric",
            },
        )

    def _record_run(self, results: List[DiscoveryResult]) -> None:
        runs = self.state.read_json("discovery_runs.json", [])
        runs.append({
            "run_id": stable_id("discovery", now_iso(), len(runs)),
            "created_at": now_iso(),
            "discovery_mode": "person_centric",
            "result_count": len(results),
            "episodes_found": sum(result.found_count for result in results),
            "information_events_found": sum(result.found_count for result in results),
            "queued": sum(result.queued_count for result in results),
            "duplicates": sum(result.duplicate_count for result in results),
            "skipped": sum(result.skipped_count for result in results),
            "failed": sum(result.failed_count for result in results),
            "results": [result.to_dict() for result in results],
        })
        self.state.write_json("discovery_runs.json", runs)


def _extract_episode_links(base_url: str, html: str) -> List[Dict[str, Any]]:
    base_path = urlparse(base_url).path.rstrip("/")
    seen: set[str] = set()
    candidates: List[Dict[str, Any]] = []
    for match in re.finditer(r"<a\b[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", html, flags=re.IGNORECASE | re.DOTALL):
        href = unescape(match.group(1)).strip()
        if not href or href.startswith("#") or href.startswith("mailto:"):
            continue
        url = urljoin(base_url, href).split("#", 1)[0]
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            continue
        if parsed.netloc != urlparse(base_url).netloc:
            continue
        path = parsed.path.rstrip("/")
        if path == base_path or not path.startswith(base_path + "/"):
            continue
        if any(skip in path.lower() for skip in ["/comments", "/privacy", "/contact", "/pricing", "/categories"]):
            continue
        if url in seen:
            continue
        seen.add(url)
        surrounding = _clean_text(html[max(0, match.start() - 700): match.end() + 1200])
        anchor_text = _clean_text(match.group(2))
        title = _title_from_context(surrounding) or anchor_text
        if title.lower().endswith("comments"):
            title = _title_from_url(url)
        candidates.append({
            "url": url,
            "title": title or _title_from_url(url),
            "description": surrounding,
            "episode_date": _extract_date(surrounding),
            "source_url": base_url,
        })
    return candidates


def _extract_title(html: str) -> Optional[str]:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    return _clean_text(match.group(1)) if match else None


def _visible_text(html: str) -> str:
    text = re.sub(r"<script\b.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    return _clean_text(text)


def _clean_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = unescape(text)
    return " ".join(text.split())


def _title_from_url(url: str) -> str:
    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    return " ".join(part.capitalize() for part in slug.replace("-", " ").split()) or url


def _title_from_context(text: str) -> Optional[str]:
    if "Episode Date:" not in text:
        return None
    before = text.split("Episode Date:", 1)[0]
    if "0 comments" in before:
        before = before.rsplit("0 comments", 1)[1]
    before = before.strip()
    for prefix in ["Technology", "Business", "Health & Fitness", "Education", "Society & Culture", "News", "Comedy"]:
        if before.startswith(prefix):
            before = before[len(prefix):].strip()
    return before[-240:].strip() or None


def _extract_date(text: str) -> Optional[str]:
    match = re.search(r"Episode Date:\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})", text)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%B %d, %Y").strftime("%Y-%m-%dT00:00:00Z")
    except ValueError:
        return None
