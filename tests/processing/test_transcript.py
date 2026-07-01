"""Transcript parsing, chunking, timestamp-link, and embedding tests."""

from src.knowledge_service.processing.transcript import (
    build_transcript_chunks,
    parse_transcript,
    timestamped_source_url,
)
from src.knowledge_service.retrieval.embedding import cosine_similarity, embed_text


def test_parse_timestamped_transcript_preserves_speaker_and_timestamps():
    raw = "[00:00:05] Host: What about tariffs?\n[00:00:12] Bill Ackman: Tariffs are a tax on consumers."

    segments = parse_transcript(raw, {"transcript_source": "published_transcript"})

    assert len(segments) == 2
    assert segments[1]["speaker"] == "Bill Ackman"
    assert segments[1]["speaker_confidence"] == 1.0
    assert segments[1]["start_seconds"] == 12.0
    assert segments[1]["text"] == "Tariffs are a tax on consumers."


def test_parse_vtt_transcript():
    raw = "WEBVTT\n\n00:01:00.000 --> 00:01:05.000\nBill Ackman: We should be careful with tariffs.\n"

    segments = parse_transcript(raw, {"transcript_source": "youtube_captions"})

    assert len(segments) == 1
    assert segments[0]["start_seconds"] == 60.0
    assert segments[0]["end_seconds"] == 65.0
    assert segments[0]["speaker"] == "Bill Ackman"


def test_parse_speaker_before_parenthesized_timestamp():
    raw = "Sam Altman [(00:03:08)] The road to AGI should be a giant power struggle."

    segments = parse_transcript(raw, {"transcript_source": "published_transcript"})

    assert len(segments) == 1
    assert segments[0]["speaker"] == "Sam Altman"
    assert segments[0]["speaker_confidence"] == 1.0
    assert segments[0]["start_seconds"] == 188.0
    assert segments[0]["text"] == "The road to AGI should be a giant power struggle."


def test_parse_podscripts_starting_point_lines():
    raw = (
        "Starting point is 00:00:00 Today, we are interviewing Satya Nadella.\n"
        "Starting point is 00:00:19 Give us a tour of the data center."
    )

    segments = parse_transcript(raw, {"transcript_source": "published_transcript"})

    assert len(segments) == 2
    assert segments[0]["speaker"] == "unknown"
    assert segments[0]["speaker_confidence"] == 0.0
    assert segments[0]["start_seconds"] == 0.0
    assert segments[0]["end_seconds"] == 19.0
    assert segments[0]["text"] == "Today, we are interviewing Satya Nadella."


def test_parse_standalone_timestamp_blocks():
    raw = "00:00:00\n\nThe following is a conversation.\n\n00:01:19\n\nThe sponsor read starts."

    segments = parse_transcript(raw, {"transcript_source": "published_transcript"})

    assert len(segments) == 2
    assert segments[0]["speaker"] == "unknown"
    assert segments[0]["start_seconds"] == 0.0
    assert segments[0]["end_seconds"] == 79.0
    assert segments[0]["text"] == "The following is a conversation."


def test_parse_html_transcript_ignores_script_and_reads_visible_text():
    raw = (
        "<html><head><script>helpers: {},</script></head><body>"
        "<p>Sam Altman <a href='https://youtube.com/watch?v=jvqFAi7vkBc&t=188'>(00:03:08)</a> "
        "The road to AGI should be a giant power struggle.</p>"
        "</body></html>"
    )

    segments = parse_transcript(raw, {"transcript_source": "published_transcript"})

    assert len(segments) == 1
    assert segments[0]["speaker"] == "Sam Altman"
    assert "helpers" not in segments[0]["text"]


def test_unknown_speaker_is_not_fabricated():
    segments = parse_transcript("[00:00:01] Tariffs increased uncertainty.", {})

    assert segments[0]["speaker"] == "unknown"
    assert segments[0]["speaker_confidence"] == 0.0


def test_malformed_transcript_returns_graceful_segment():
    segments = parse_transcript("A transcript without timestamps still has text.", {})

    assert len(segments) == 1
    assert segments[0]["start_seconds"] is None
    assert segments[0]["speaker"] == "unknown"


def test_timestamped_youtube_link_generation():
    url = timestamped_source_url("https://www.youtube.com/watch?v=abc123", 75.4)

    assert url == "https://www.youtube.com/watch?v=abc123&t=75s"


def test_transcript_chunks_include_embedding_context_and_citation():
    segments = parse_transcript(
        "[00:00:01] Host: Question on tariffs.\n"
        "[00:00:10] Bill Ackman: Tariffs raise prices.\n"
        "[00:00:18] Bill Ackman: They also change capital allocation.",
        {"transcript_source": "published_transcript"},
    )
    chunks = build_transcript_chunks(segments, {
        "transcript_id": "episode-1",
        "source_url": "https://www.youtube.com/watch?v=abc123",
        "show": "Test Show",
        "episode": "Tariff Talk",
    })

    bill_chunks = [chunk for chunk in chunks if chunk["speaker"] == "Bill Ackman"]
    assert len(bill_chunks) == 1
    assert bill_chunks[0]["timestamp_start"] == 10.0
    assert bill_chunks[0]["timestamped_source_url"].endswith("t=10s")
    assert "Question on tariffs" in bill_chunks[0]["surrounding_context"]
    assert len(bill_chunks[0]["embedding"]) == 64
    assert bill_chunks[0]["citations"][0]["quote"] == "Tariffs raise prices. They also change capital allocation."


def test_embedding_similarity_prefers_matching_terms():
    query = embed_text("tariffs")
    relevant = embed_text("Tariffs raise prices")
    unrelated = embed_text("cloud infrastructure deployment")

    assert cosine_similarity(query, relevant) > cosine_similarity(query, unrelated)
