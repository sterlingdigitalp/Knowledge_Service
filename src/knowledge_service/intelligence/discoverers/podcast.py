"""Podcast information event discoverer — fully implemented."""

from __future__ import annotations

import time
from datetime import datetime
from html import unescape
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse
import re

import httpx

from ..discovery import DiscoveryResult
from ..models import (
    DiscoveredEpisode,
    EpisodeStatus,
    InformationEventType,
    IntelligenceProfile,
    PodcastListKind,
    PodcastSource,
)
from .base import DiscoveryContext, InformationEventDiscoverer


class PodcastDiscoverer(InformationEventDiscoverer):
    @property
    def discoverer_id(self) -> str:
        return "podcast"

    @property
    def event_types(self) -> List[str]:
        return [InformationEventType.PODCAST_EPISODE.value]

    def discover(self, profile: IntelligenceProfile, context: DiscoveryContext) -> List[DiscoveryResult]:
        if not self.is_enabled(profile):
            return []
        results: List[DiscoveryResult] = []
        for podcast in profile.enabled_podcasts():
            results.append(self._discover_podcast(profile, podcast, context))
        return results

    def _discover_podcast(
        self,
        profile: IntelligenceProfile,
        podcast: PodcastSource,
        context: DiscoveryContext,
    ) -> DiscoveryResult:
        started = time.perf_counter()
        result = DiscoveryResult(profile_id=profile.profile_id, podcast_name=podcast.name, status="success")
        try:
            candidates = self._episode_candidates(podcast, context.timeout_seconds)
            result.found_count = len(candidates)
            for candidate in candidates[: max(1, podcast.max_episodes)]:
                episode = self._episode_from_candidate(profile, podcast, candidate, context)
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
                should_queue, duplicate_key, duplicate_of = context.dedupe.should_queue(episode)
                if not should_queue:
                    episode.status = EpisodeStatus.DUPLICATE
                    episode.duplicate_of = duplicate_of
                    episode.error = f"Duplicate {duplicate_key}"
                    result.duplicate_count += 1
                else:
                    episode.status = EpisodeStatus.QUEUED
                    context.dedupe.register_discovery(episode)
                    result.queued_count += 1
                result.episodes.append(episode)
            context.dedupe.save()
        except Exception as exc:
            result.status = "failed"
            result.error = str(exc)
            result.failed_count += 1
        result.elapsed_seconds = time.perf_counter() - started
        return result

    def _episode_candidates(self, podcast: PodcastSource, timeout_seconds: float) -> List[Dict[str, Any]]:
        if podcast.episode_urls:
            return [
                {"url": url, "title": _title_from_url(url), "description": "", "episode_date": None, "source_url": podcast.url}
                for url in podcast.episode_urls
            ]
        if podcast.discovery_mode not in {"podscripts", "page", "html"}:
            raise ValueError(f"Unsupported discovery mode: {podcast.discovery_mode}")
        response = httpx.get(
            podcast.url,
            timeout=timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "Knowledge_Service/PodcastDiscoverer"},
        )
        response.raise_for_status()
        candidates = _extract_episode_links(podcast.url, response.text)
        if not candidates:
            page_title = _extract_title(response.text) or _title_from_url(podcast.url)
            candidates = [{
                "url": podcast.url,
                "title": page_title,
                "description": _visible_text(response.text)[:1000],
                "episode_date": None,
                "source_url": podcast.url,
            }]
        return candidates

    def _episode_from_candidate(
        self,
        profile: IntelligenceProfile,
        podcast: PodcastSource,
        candidate: Dict[str, Any],
        context: DiscoveryContext,
    ) -> DiscoveredEpisode:
        title = candidate.get("title") or _title_from_url(candidate["url"])
        episode_date = candidate.get("episode_date") or _extract_date(" ".join([title, candidate.get("description", "")]))
        source_id = ""
        if context.route_registry is not None:
            source_id = context.route_registry.resolve_source_id(podcast_name=podcast.name, url=candidate["url"])
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
                "discoverer_id": self.discoverer_id,
                "podcast_id": podcast.podcast_id,
                "podcast_kind": podcast.kind.value,
                "discovery_mode": podcast.discovery_mode,
                "discovery_strategy": "person_centric",
            },
        )


def _extract_episode_links(base_url: str, html: str) -> List[Dict[str, Any]]:
    from ..discovery import _extract_episode_links as legacy

    return legacy(base_url, html)


def _extract_title(html: str) -> Optional[str]:
    from ..discovery import _extract_title as legacy

    return legacy(html)


def _visible_text(html: str) -> str:
    from ..discovery import _visible_text as legacy

    return legacy(html)


def _title_from_url(url: str) -> str:
    from ..discovery import _title_from_url as legacy

    return legacy(url)


def _extract_date(text: str) -> Optional[str]:
    from ..discovery import _extract_date as legacy

    return legacy(text)