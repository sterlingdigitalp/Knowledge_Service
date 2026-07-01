"""Transcript provider contract tests."""

from pathlib import Path
import sys
import types
from unittest.mock import patch

from src.knowledge_service.interfaces.provider import ProviderRequest, ProviderResponse, ProviderType
from src.knowledge_service.providers.transcript_provider import TranscriptProvider


def test_direct_published_transcript_response_preserves_provenance():
    provider = TranscriptProvider("transcript-test")
    provider.initialize({})

    response = provider.execute(ProviderRequest(
        target="https://example.com/transcript",
        provider_type=ProviderType.API,
        options={
            "transcript_text": "[00:00:12] Bill Ackman: Tariffs are a tax.",
            "metadata": {"show": "Test Show", "episode": "Tariffs", "episode_date": "2026-06-01T00:00:00Z"},
        },
    ))

    assert response.error is None
    assert response.content == "[00:00:12] Bill Ackman: Tariffs are a tax."
    assert response.metadata["source_type"] == "video_transcript"
    assert response.metadata["transcript_source"] == "published_transcript"
    assert response.metadata["acquisition_status"] == "success"
    assert response.metadata["provider"] == "transcript-test"
    assert response.metadata["transcript_segments"][0]["speaker"] == "Bill Ackman"


def test_structured_segments_supported():
    provider = TranscriptProvider("transcript-test")
    provider.initialize({})

    response = provider.execute(ProviderRequest(
        target="https://example.com/episode",
        provider_type=ProviderType.API,
        options={
            "segments": [{"start_seconds": 3, "end_seconds": 7, "speaker": "Bill Ackman", "text": "Tariffs matter."}],
        },
    ))

    assert response.error is None
    assert "[00:00:03] Bill Ackman: Tariffs matter." in response.content
    assert response.metadata["transcript_segments"][0]["start_seconds"] == 3.0


def test_published_html_response_extracts_visible_transcript_text():
    class Response:
        is_success = True
        status_code = 200
        headers = {"content-type": "text/html; charset=utf-8"}
        text = (
            "<html><head><script>helpers: {},</script></head><body>"
            "<p>Sam Altman <a href='https://youtube.com/watch?v=jvqFAi7vkBc&t=188'>(00:03:08)</a> "
            "The road to AGI should be a giant power struggle.</p>"
            "</body></html>"
        )

    provider = TranscriptProvider("transcript-test")
    provider.initialize({})

    with patch("src.knowledge_service.providers.transcript_provider.httpx.get", return_value=Response()) as get:
        response = provider.execute(ProviderRequest(
            target="https://example.com/transcript",
            provider_type=ProviderType.API,
            options={"allow_fallback": False},
        ))

    assert response.error is None
    assert response.content_type == "text/transcript"
    assert "helpers" not in response.content
    assert response.metadata["transcript_segments"][0]["speaker"] == "Sam Altman"
    assert response.metadata["transcript_segments"][0]["start_seconds"] == 188.0
    assert get.call_args.kwargs["follow_redirects"] is True
    assert "User-Agent" in get.call_args.kwargs["headers"]


def test_youtube_dependency_missing_is_graceful():
    provider = TranscriptProvider("transcript-test")
    provider.initialize({})

    with patch.dict(sys.modules, {"youtube_transcript_api": None}):
        response = provider.execute(ProviderRequest(
            target="https://www.youtube.com/watch?v=abc123",
            provider_type=ProviderType.API,
            options={"source": "youtube_captions", "allow_fallback": False},
        ))

    assert response.error is not None
    assert response.error.code == "YOUTUBE_TRANSCRIPT_DEPENDENCY_MISSING"


def test_youtube_captions_support_installed_fetch_api():
    fake_module = types.ModuleType("youtube_transcript_api")

    class FakeYouTubeTranscriptApi:
        def fetch(self, video_id, languages):
            assert video_id == "abc123"
            assert languages == ["en"]
            return [types.SimpleNamespace(text="Caption text", start=1.5, duration=2.0)]

    fake_module.YouTubeTranscriptApi = FakeYouTubeTranscriptApi
    provider = TranscriptProvider("transcript-test")
    provider.initialize({})

    with patch.dict(sys.modules, {"youtube_transcript_api": fake_module}):
        response = provider.execute(ProviderRequest(
            target="https://www.youtube.com/watch?v=abc123",
            provider_type=ProviderType.API,
            options={"source": "youtube_captions", "allow_fallback": False, "languages": ["en"]},
        ))

    assert response.error is None
    assert response.metadata["transcript_source"] == "youtube_captions"
    assert response.metadata["transcript_segments"][0]["start_seconds"] == 1.5
    assert response.metadata["transcript_segments"][0]["end_seconds"] == 3.5
    assert response.metadata["transcript_segments"][0]["speaker"] == "unknown"


def test_whisper_missing_input_is_graceful():
    provider = TranscriptProvider("transcript-test")
    provider.initialize({})

    response = provider.execute(ProviderRequest(
        target="https://example.com/audio.mp3",
        provider_type=ProviderType.API,
        options={"source": "whisper_fallback"},
    ))

    assert response.error is not None
    assert response.error.code == "WHISPER_INPUT_MISSING"


def test_whisper_youtube_target_downloads_audio_when_needed(tmp_path):
    audio_path = tmp_path / "clip.mp3"
    audio_path.write_bytes(b"audio")
    fake_whisper = types.ModuleType("whisper")

    class FakeModel:
        def transcribe(self, path, **options):
            assert path == str(audio_path)
            assert options["language"] == "en"
            return {"segments": [{"start": 0.0, "end": 2.0, "text": "Whisper text"}]}

    fake_whisper.load_model = lambda model_name: FakeModel()
    provider = TranscriptProvider("transcript-test")
    provider.initialize({"whisper_model": "tiny"})
    provider._download_youtube_audio = lambda target, options: ProviderResponse(content=str(audio_path), content_type="audio/mpeg")

    with patch.dict(sys.modules, {"whisper": fake_whisper}):
        response = provider.execute(ProviderRequest(
            target="https://www.youtube.com/watch?v=abc123",
            provider_type=ProviderType.API,
            options={"source": "whisper_fallback", "allow_fallback": False, "language": "en"},
        ))

    assert response.error is None
    assert response.metadata["transcript_source"] == "whisper_fallback"
    assert response.metadata["transcript_segments"][0]["text"] == "Whisper text"
    assert response.metadata["downloaded_audio_path"] == str(audio_path)
