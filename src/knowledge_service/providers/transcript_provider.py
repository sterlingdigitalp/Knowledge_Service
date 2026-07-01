"""Transcript provider with published, YouTube-caption, and Whisper fallback paths."""

from datetime import datetime, timezone
from pathlib import Path
import tempfile
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import httpx

from ..interfaces.provider import (
    HealthCheckResult,
    HealthStatus,
    InitResult,
    Provider,
    ProviderError,
    ProviderRequest,
    ProviderResponse,
)
from ..processing.transcript import TRANSCRIPT_SOURCE_TYPE, extract_transcript_text, parse_transcript


class TranscriptProvider(Provider):
    """Acquire transcript text while preserving provenance metadata.

    Priority order:
    1. Explicit or published transcript text/URL.
    2. YouTube captions via optional `youtube_transcript_api`.
    3. Whisper fallback via optional local `whisper` installation.
    """

    def __init__(self, name: str = "transcript-provider"):
        self._name = name
        self._config: Dict[str, Any] = {}
        self._is_initialized = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> Dict[str, Any]:
        return {
            "can_api": True,
            "can_fetch_api": True,
            "can_crawl": False,
            "can_search": False,
            "can_read_rss": False,
            "can_file_processor": True,
            "can_process_files": True,
            "can_query_database": False,
            "supported_content_types": [
                "text/transcript",
                "text/vtt",
                "text/srt",
                "application/transcript+json",
            ],
            "transcript_sources": ["published_transcript", "youtube_captions", "whisper_fallback"],
        }

    def initialize(self, config: Dict[str, Any]) -> InitResult:
        self._config = config or {}
        self._is_initialized = True
        return InitResult(name=self._name, version="1.0", capabilities=self.capabilities)

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        if not self._is_initialized:
            self.initialize({})

        options = request.options or {}
        base_metadata = self._base_metadata(request)

        explicit = options.get("transcript_text")
        if explicit is not None:
            return self._success(
                content=str(explicit),
                content_type=options.get("content_type", "text/transcript"),
                metadata={**base_metadata, **options.get("metadata", {}), "transcript_source": "published_transcript"},
            )

        segments = options.get("segments") or options.get("transcript_segments")
        if segments is not None:
            content = self._segments_to_text(segments)
            return self._success(
                content=content,
                content_type="application/transcript+json",
                metadata={
                    **base_metadata,
                    **options.get("metadata", {}),
                    "transcript_source": "published_transcript",
                    "transcript_segments": segments,
                },
            )

        source_preference = options.get("source")
        if source_preference in {None, "published", "published_transcript"} and not self._looks_like_youtube(request.target):
            published = self._fetch_published_transcript(request.target, options)
            if published.error is None:
                return published
            if not options.get("allow_fallback", True):
                return published

        if source_preference in {None, "youtube", "youtube_captions"} and self._looks_like_youtube(request.target):
            captions = self._fetch_youtube_captions(request.target, options, base_metadata)
            if captions.error is None:
                return captions
            if not options.get("allow_fallback", True):
                return captions

        if source_preference in {None, "whisper", "whisper_fallback"}:
            return self._whisper_fallback(request, options, base_metadata)

        return ProviderResponse(error=ProviderError(
            code="TRANSCRIPT_NOT_FOUND",
            message="No transcript source produced content",
            retryable=False,
            recoverable=True,
        ))

    def health(self) -> HealthCheckResult:
        return HealthCheckResult(status=HealthStatus.HEALTHY)

    def shutdown(self) -> None:
        self._is_initialized = False

    def _success(self, content: str, content_type: str, metadata: Dict[str, Any]) -> ProviderResponse:
        metadata = dict(metadata)
        metadata.setdefault("source_type", TRANSCRIPT_SOURCE_TYPE)
        metadata.setdefault("provider", self.name)
        metadata.setdefault("acquisition_status", "success")
        metadata.setdefault("acquisition_timestamp", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        metadata.setdefault("transcript_confidence", self._confidence_for(metadata.get("transcript_source")))
        metadata.setdefault("transcript_segments", parse_transcript(content, metadata))
        return ProviderResponse(
            content=content,
            content_type=content_type,
            status_code=200,
            metadata=metadata,
        )

    def _base_metadata(self, request: ProviderRequest) -> Dict[str, Any]:
        context = request.context or {}
        options = request.options or {}
        metadata = {
            "source_url": request.target,
            "url": request.target,
            "provider": self.name,
            "source_type": TRANSCRIPT_SOURCE_TYPE,
            "acquisition_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        metadata.update(context.get("metadata", {}))
        metadata.update(options.get("metadata", {}))
        video_id = metadata.get("video_id") or self._youtube_video_id(request.target)
        if video_id:
            metadata["video_id"] = video_id
            metadata.setdefault("transcript_id", video_id)
        metadata.setdefault("transcript_id", metadata.get("episode_id") or metadata.get("video_id") or request.target)
        return metadata

    def _fetch_published_transcript(self, target: str, options: Dict[str, Any]) -> ProviderResponse:
        timeout = options.get("timeout_ms", self._config.get("timeout_ms", 15000)) / 1000.0
        headers = dict(options.get("headers") or {})
        headers.setdefault(
            "User-Agent",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
        )
        try:
            response = httpx.get(target, timeout=timeout, follow_redirects=True, headers=headers)
        except Exception as exc:
            return ProviderResponse(error=ProviderError(
                code="PUBLISHED_TRANSCRIPT_UNAVAILABLE",
                message=f"Published transcript unavailable: {exc}",
                retryable=True,
                recoverable=True,
            ))
        if not response.is_success:
            return ProviderResponse(error=ProviderError(
                code="PUBLISHED_TRANSCRIPT_UNAVAILABLE",
                message=f"Published transcript returned HTTP {response.status_code}",
                provider_specific_code=str(response.status_code),
                retryable=response.status_code >= 500,
                recoverable=True,
            ))
        metadata = {
            **self._base_metadata(ProviderRequest(target=target, provider_type=options.get("provider_type"), options=options)),
            "transcript_source": "published_transcript",
        }
        content_type = response.headers.get("content-type", "text/transcript").split(";")[0]
        content = extract_transcript_text(response.text) if content_type in {"text/html", "application/xhtml+xml"} else response.text
        if content_type in {"text/html", "application/xhtml+xml"}:
            content_type = "text/transcript"
        return self._success(content, content_type, metadata)

    def _fetch_youtube_captions(self, target: str, options: Dict[str, Any], base_metadata: Dict[str, Any]) -> ProviderResponse:
        video_id = self._youtube_video_id(target)
        if not video_id:
            return ProviderResponse(error=ProviderError(
                code="INVALID_YOUTUBE_URL",
                message="Could not determine YouTube video id",
                retryable=False,
                recoverable=True,
            ))
        try:
            from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore
        except Exception:
            return ProviderResponse(error=ProviderError(
                code="YOUTUBE_TRANSCRIPT_DEPENDENCY_MISSING",
                message="youtube_transcript_api is not installed",
                retryable=False,
                recoverable=True,
            ))
        try:
            languages = options.get("languages", ["en"])
            if hasattr(YouTubeTranscriptApi, "get_transcript"):
                fetched = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
            else:
                fetched = YouTubeTranscriptApi().fetch(video_id, languages=languages)
        except Exception as exc:
            return ProviderResponse(error=ProviderError(
                code="YOUTUBE_CAPTIONS_UNAVAILABLE",
                message=f"YouTube captions unavailable: {exc}",
                retryable=False,
                recoverable=True,
            ))

        segments = []
        for index, item in enumerate(fetched):
            item_data = item if isinstance(item, dict) else getattr(item, "__dict__", {})
            start = float(item_data.get("start", 0.0))
            duration = float(item_data.get("duration", 0.0))
            segments.append({
                "segment_id": f"yt-{index}",
                "start_seconds": start,
                "end_seconds": start + duration,
                "speaker": "unknown",
                "speaker_confidence": 0.0,
                "text": item_data.get("text", ""),
                "confidence": 0.85,
            })
        content = self._segments_to_text(segments)
        return self._success(
            content=content,
            content_type="text/transcript",
            metadata={
                **base_metadata,
                "video_id": video_id,
                "transcript_id": base_metadata.get("transcript_id") or video_id,
                "transcript_source": "youtube_captions",
                "transcript_segments": segments,
            },
        )

    def _whisper_fallback(self, request: ProviderRequest, options: Dict[str, Any], base_metadata: Dict[str, Any]) -> ProviderResponse:
        audio_path = options.get("audio_path")
        downloaded_audio_path: Optional[str] = None
        if not audio_path and options.get("target_is_audio"):
            audio_path = request.target
        if not audio_path and self._looks_like_youtube(request.target):
            downloaded = self._download_youtube_audio(request.target, options)
            if downloaded.error is not None:
                return downloaded
            audio_path = downloaded.content
            downloaded_audio_path = downloaded.content
        if not audio_path:
            return ProviderResponse(error=ProviderError(
                code="WHISPER_INPUT_MISSING",
                message="Whisper fallback requires audio_path, target_is_audio=True, or a YouTube URL for yt-dlp extraction",
                retryable=False,
                recoverable=True,
            ))
        if not Path(str(audio_path)).exists():
            return ProviderResponse(error=ProviderError(
                code="WHISPER_INPUT_MISSING",
                message=f"Audio file not found: {audio_path}",
                retryable=False,
                recoverable=True,
            ))
        try:
            import whisper  # type: ignore
        except Exception:
            return ProviderResponse(error=ProviderError(
                code="WHISPER_DEPENDENCY_MISSING",
                message="whisper is not installed",
                retryable=False,
                recoverable=True,
            ))
        try:
            model_name = options.get("whisper_model", self._config.get("whisper_model", "base"))
            model = whisper.load_model(model_name)
            transcribe_options = dict(options.get("whisper_options") or {})
            if "language" in options and "language" not in transcribe_options:
                transcribe_options["language"] = options["language"]
            result = model.transcribe(str(audio_path), **transcribe_options)
        except Exception as exc:
            return ProviderResponse(error=ProviderError(
                code="WHISPER_TRANSCRIPTION_FAILED",
                message=f"Whisper transcription failed: {exc}",
                retryable=False,
                recoverable=True,
            ))

        segments = []
        for index, item in enumerate(result.get("segments", [])):
            segments.append({
                "segment_id": f"whisper-{index}",
                "start_seconds": item.get("start"),
                "end_seconds": item.get("end"),
                "speaker": "unknown",
                "speaker_confidence": 0.0,
                "text": item.get("text", ""),
                "confidence": 0.65,
            })
        content = self._segments_to_text(segments)
        return self._success(
            content=content,
            content_type="text/transcript",
            metadata={
                **base_metadata,
                "source_url": str(audio_path),
                "original_source_url": request.target,
                "downloaded_audio_path": downloaded_audio_path,
                "transcript_source": "whisper_fallback",
                "transcript_segments": segments,
            },
        )

    def _download_youtube_audio(self, target: str, options: Dict[str, Any]) -> ProviderResponse:
        try:
            from yt_dlp import YoutubeDL  # type: ignore
            from yt_dlp.utils import download_range_func  # type: ignore
        except Exception:
            return ProviderResponse(error=ProviderError(
                code="YTDLP_DEPENDENCY_MISSING",
                message="yt-dlp is not installed",
                retryable=False,
                recoverable=True,
            ))

        video_id = self._youtube_video_id(target) or "youtube-audio"
        audio_dir = Path(str(options.get("audio_download_dir") or tempfile.mkdtemp(prefix="knowledge_service_whisper_")))
        audio_dir.mkdir(parents=True, exist_ok=True)
        output_template = str(audio_dir / f"{video_id}.%(ext)s")
        ydl_options: Dict[str, Any] = {
            "format": options.get("yt_dlp_format", "bestaudio/best"),
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": options.get("audio_codec", "mp3"),
                "preferredquality": str(options.get("audio_quality", "64")),
            }],
        }
        if options.get("audio_clip_duration_seconds") is not None:
            start = float(options.get("audio_clip_start_seconds", 0.0))
            duration = float(options["audio_clip_duration_seconds"])
            ydl_options["download_ranges"] = download_range_func(None, [(start, start + duration)])
            ydl_options["force_keyframes_at_cuts"] = True
        if options.get("cookies_from_browser"):
            ydl_options["cookiesfrombrowser"] = tuple(options["cookies_from_browser"])

        try:
            with YoutubeDL(ydl_options) as ydl:
                ydl.download([target])
        except Exception as exc:
            return ProviderResponse(error=ProviderError(
                code="YTDLP_AUDIO_DOWNLOAD_FAILED",
                message=f"yt-dlp audio download failed: {exc}",
                retryable=True,
                recoverable=True,
            ))

        candidates = sorted(
            [path for path in audio_dir.glob(f"{video_id}.*") if path.is_file()],
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            return ProviderResponse(error=ProviderError(
                code="YTDLP_AUDIO_NOT_FOUND",
                message=f"yt-dlp completed but no audio file was found in {audio_dir}",
                retryable=True,
                recoverable=True,
            ))
        return ProviderResponse(
            content=str(candidates[0]),
            content_type="audio/mpeg",
            status_code=200,
            metadata={"audio_path": str(candidates[0]), "audio_download_dir": str(audio_dir)},
        )

    def _segments_to_text(self, segments: List[Dict[str, Any]]) -> str:
        lines = []
        for segment in segments:
            start = segment.get("start_seconds", segment.get("start"))
            speaker = segment.get("speaker") or "unknown"
            text = segment.get("text") or ""
            timestamp = self._format_timestamp(float(start or 0.0))
            lines.append(f"[{timestamp}] {speaker}: {text}")
        return "\n".join(lines)

    def _looks_like_youtube(self, target: str) -> bool:
        host = urlparse(target).netloc.lower()
        return "youtube.com" in host or "youtu.be" in host

    def _youtube_video_id(self, target: str) -> Optional[str]:
        parsed = urlparse(target)
        host = parsed.netloc.lower()
        if "youtu.be" in host:
            return parsed.path.strip("/") or None
        if "youtube.com" in host:
            query = parse_qs(parsed.query)
            if query.get("v"):
                return query["v"][0]
            parts = [part for part in parsed.path.split("/") if part]
            if len(parts) >= 2 and parts[0] in {"embed", "shorts"}:
                return parts[1]
        return None

    def _confidence_for(self, transcript_source: Optional[str]) -> float:
        if transcript_source == "published_transcript":
            return 0.95
        if transcript_source == "youtube_captions":
            return 0.85
        if transcript_source == "whisper_fallback":
            return 0.65
        return 0.8

    def _format_timestamp(self, seconds: float) -> str:
        total = int(seconds)
        hours = total // 3600
        minutes = (total % 3600) // 60
        secs = total % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
