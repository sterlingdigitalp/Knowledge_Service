"""Corpus integrity verification."""

from __future__ import annotations

from typing import Any, Dict, List, Set

from .corpus import CorpusManager
from .models import EpisodeStatus
from .route_registry import AcquisitionRouteRegistry
from .state import FileStateStore


def audit_corpus(state: FileStateStore) -> Dict[str, Any]:
    corpus = CorpusManager(state)
    registry = AcquisitionRouteRegistry(state)
    episodes = corpus.episodes()
    objects = corpus.knowledge_objects()
    profiles = {p.profile_id: p for p in corpus.load_profiles()}

    docs = [o for o in objects if o.get("type") == "document"]
    chunks = [o for o in objects if o.get("type") == "chunk"]
    doc_ids = {d.get("id") for d in docs}
    chunk_parent_ids: Set[str] = set()
    for chunk in chunks:
        parent = (chunk.get("structured_data") or {}).get("parent_id") or chunk.get("parent_id")
        if parent:
            chunk_parent_ids.add(parent)

    issues: List[Dict[str, Any]] = []
    episode_ids = {e.episode_id for e in episodes}
    processed = [e for e in episodes if e.status == EpisodeStatus.PROCESSED]

    for episode in processed:
        if not episode.knowledge_object_ids:
            issues.append({"code": "MISSING_KNOWLEDGE_OBJECTS", "episode_id": episode.episode_id})
        if not episode.acquisition_route:
            issues.append({"code": "MISSING_ACQUISITION_ROUTE", "episode_id": episode.episode_id})
        if not episode.source_id:
            issues.append({"code": "MISSING_SOURCE_ID", "episode_id": episode.episode_id})
        if episode.profile_id not in profiles:
            issues.append({"code": "ORPHAN_PROFILE", "episode_id": episode.episode_id, "profile_id": episode.profile_id})
        if not episode.transcript_provenance:
            issues.append({"code": "MISSING_PROVENANCE", "episode_id": episode.episode_id})

    for doc in docs:
        meta = (doc.get("structured_data") or {}).get("metadata", {})
        episode_id = meta.get("episode_id")
        if not episode_id:
            issues.append({"code": "DOC_MISSING_EPISODE", "document_id": doc.get("id")})
        elif episode_id not in episode_ids:
            issues.append({"code": "ORPHAN_DOCUMENT", "document_id": doc.get("id"), "episode_id": episode_id})
        if not meta.get("acquisition_route") and not meta.get("transcript_provenance"):
            issues.append({"code": "DOC_MISSING_ROUTE_PROVENANCE", "document_id": doc.get("id")})

    for chunk in chunks:
        parent = (chunk.get("structured_data") or {}).get("parent_id") or chunk.get("parent_id")
        if parent and parent not in doc_ids:
            issues.append({"code": "ORPHAN_CHUNK", "chunk_id": chunk.get("id"), "parent_id": parent})
        embedding = (chunk.get("structured_data") or {}).get("embedding")
        if embedding is None:
            issues.append({"code": "CHUNK_MISSING_EMBEDDING", "chunk_id": chunk.get("id")})

    orphaned_docs = doc_ids - {e.episode_id for e in processed}
    for doc_id in orphaned_docs:
        if any(doc.get("id") == doc_id for doc in docs):
            meta = next((d for d in docs if d.get("id") == doc_id), {})
            if not (meta.get("structured_data") or {}).get("metadata", {}).get("intelligence_collection"):
                issues.append({"code": "UNLINKED_DOCUMENT", "document_id": doc_id})

    dedupe = state.read_json("dedupe.json", {})
    transcript_hashes = dedupe.get("transcript_hashes", {})
    if len(transcript_hashes) < len(processed):
        issues.append({
            "code": "TRANSCRIPT_HASH_GAP",
            "message": f"{len(processed)} processed but {len(transcript_hashes)} transcript hashes",
        })

    registry.refresh_all_confidence(_episode_metrics(episodes))
    status = "pass" if not issues else "fail"

    return {
        "status": status,
        "episodes": len(episodes),
        "processed_episodes": len(processed),
        "documents": len(docs),
        "chunks": len(chunks),
        "embeddings": sum(1 for c in chunks if (c.get("structured_data") or {}).get("embedding")),
        "issues": issues,
        "issue_count": len(issues),
        "chains_verified": len(processed),
        "registry_sources": registry.summary()["source_count"],
    }


def _episode_metrics(episodes: List[Any]) -> List[Dict[str, Any]]:
    return [
        {
            "source_id": e.source_id,
            "acquisition_route": e.acquisition_route,
            "route_confidence": e.route_confidence,
        }
        for e in episodes
        if e.acquisition_route
    ]


def generate_corpus_audit_markdown(audit: Dict[str, Any]) -> str:
    lines = [
        "# Corpus Audit",
        "",
        f"**Status:** {audit['status'].upper()}",
        "",
        "## Summary",
        f"- Episodes: {audit['episodes']}",
        f"- Processed: {audit['processed_episodes']}",
        f"- Documents: {audit['documents']}",
        f"- Chunks: {audit['chunks']}",
        f"- Embeddings: {audit['embeddings']}",
        f"- Issues: {audit['issue_count']}",
        "",
        "## Verification Chain",
        "Transcript → KnowledgeObject → Chunks → Embeddings → Information Event → Source Route → Profile",
        "",
    ]
    if audit["issues"]:
        lines.append("## Issues")
        for issue in audit["issues"]:
            lines.append(f"- `{issue['code']}`: {issue}")
    else:
        lines.append("No integrity issues detected.")
    return "\n".join(lines)