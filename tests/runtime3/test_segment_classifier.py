"""Tests for Agent A — transcript segmentation."""

from __future__ import annotations

from knowledge_service.runtime3.models import SegmentType
from knowledge_service.runtime3.segmentation.classifier import SegmentClassifier
from knowledge_service.runtime3.segmentation.patterns import classify_segment_text


def test_classify_sponsor_segment():
    text = "Thanks to our partner Mercury. Visit mercury.com slash Command to learn more."
    segment_type, confidence = classify_segment_text(text, position_ratio=0.02)
    assert segment_type == SegmentType.SPONSOR
    assert confidence >= 0.55


def test_classify_intro_segment():
    text = "Welcome to the All-In Podcast. Nate Silver joins the pod!"
    segment_type, _ = classify_segment_text(text, position_ratio=0.01)
    assert segment_type in {SegmentType.INTRO, SegmentType.INTERVIEW}


def test_classify_meta_request():
    text = "If you want to help me out and help me figure out where next that should go in the world"
    segment_type, _ = classify_segment_text(text, position_ratio=0.95)
    assert segment_type == SegmentType.META_REQUEST


def test_classify_news_segment():
    text = "OpenAI announced a new coding agent that uses RLVR training for enterprise deployments."
    segment_type, _ = classify_segment_text(text, position_ratio=0.5)
    assert segment_type in {SegmentType.NEWS, SegmentType.DISCUSSION}


def test_classify_episode_document():
    classifier = SegmentClassifier()
    document = {
        "id": "doc-1",
        "type": "document",
        "source_url": "https://example.com",
        "structured_data": {
            "show": "Dwarkesh Podcast",
            "metadata": {"episode_id": "ep-1", "podcast_name": "Dwarkesh Podcast"},
            "transcript_segments": [
                {"segment_id": "s0", "text": "Visit mercury.com for banking.", "start_seconds": 0, "speaker": "host"},
                {"segment_id": "s1", "text": "Grant Sanderson discussed AI progress in mathematics at the International Math Olympiad level.", "start_seconds": 120, "speaker": "host"},
                {"segment_id": "s2", "text": "The conversation continued on model capabilities and benchmark trends.", "start_seconds": 240, "speaker": "guest"},
            ],
        },
    }
    segments = classifier.classify_episode(document, {"episode_id": "ep-1"})
    assert len(segments) == 3
    assert segments[0].segment_type == SegmentType.SPONSOR
    assert segments[1].segment_type in {SegmentType.NEWS, SegmentType.DISCUSSION, SegmentType.INTERVIEW}
    assert segments[2].segment_type in {
        SegmentType.DISCUSSION, SegmentType.QA, SegmentType.INTERVIEW, SegmentType.NEWS,
    }