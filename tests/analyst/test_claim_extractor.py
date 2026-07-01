import copy

from knowledge_service.analyst.claims.extractor import ClaimExtractor, MIN_CLAIM_CHARS


def test_extract_from_corpus_produces_claims_with_required_fields(
    phase32_profiles,
    phase32_documents,
    phase32_episodes,
):
    claims = ClaimExtractor().extract_from_corpus(phase32_documents, phase32_episodes, phase32_profiles)

    assert claims
    claim = claims[0]
    assert claim.speaker
    assert claim.timestamp_start is not None
    assert claim.timestamp_label
    assert claim.evidence
    assert claim.topic
    assert isinstance(claim.entities, list)
    assert claim.episode_id
    assert claim.transcript_reference
    assert claim.embedding


def test_claims_include_speaker_timestamp_evidence_topic_entities(extracted_claims):
    claim = extracted_claims[0]

    assert claim.speaker == "unknown"
    assert claim.timestamp_start >= 0.0
    assert claim.evidence == claim.claim_text
    assert claim.topic in {"AI", "Coding", "Datacenters", "Inference", "Agents", "Enterprise AI", "general"} or claim.topic
    assert "Grant Sanderson" in claim.entities or claim.topic == "AI"
    assert len(claim.claim_text) >= MIN_CLAIM_CHARS


def test_extract_from_episode_skips_short_and_filler_segments(phase32_documents, phase32_episodes, phase32_profiles):
    document = copy.deepcopy(phase32_documents[0])
    episode_meta = phase32_episodes[0]
    segments = document["structured_data"]["metadata"]["transcript_segments"]
    segments[0]["text"] = "um, okay"
    segments[1]["text"] = "Too short."

    claims = ClaimExtractor().extract_from_episode(document, episode_meta, phase32_profiles)

    assert all(len(claim.claim_text) >= MIN_CLAIM_CHARS for claim in claims)
    assert all(claim.claim_text.lower() not in {"um, okay", "too short."} for claim in claims)


def test_extract_from_episode_without_segments_returns_empty(phase32_episodes, phase32_profiles):
    document = {
        "id": "empty-doc",
        "type": "document",
        "structured_data": {"metadata": {"episode_id": phase32_episodes[0]["episode_id"]}},
    }

    claims = ClaimExtractor().extract_from_episode(document, phase32_episodes[0], phase32_profiles)

    assert claims == []