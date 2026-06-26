"""Hierarchy Assembly — Reconstruct complete document trees from stored Knowledge Objects"""

from typing import List, Optional, Dict
from ..knowledge_object import KnowledgeObject, KnowledgeType
from .interfaces import RetrievalResult, RetrievalWarning


def assemble_hierarchy(
    document_ko: KnowledgeObject,
    children: List[KnowledgeObject],
) -> List[KnowledgeObject]:
    """Assemble a document hierarchy: document + chunks + relationships, ordered."""
    result: List[KnowledgeObject] = [document_ko]

    chunks = [ko for ko in children if ko.type == KnowledgeType.CHUNK]
    relationships = [ko for ko in children if ko.type == KnowledgeType.RELATIONSHIP]

    chunks.sort(key=lambda c: (c.chunk_index or 0, c.id))
    result.extend(chunks)
    result.extend(relationships)

    return result


def rebuild_tree(
    document_id: str,
    all_objects: Dict[str, KnowledgeObject],
) -> RetrievalResult:
    """Rebuild a complete document tree from a flat dictionary of all objects."""
    doc = all_objects.get(document_id)
    if doc is None:
        return RetrievalResult(
            objects=[], total_count=0, returned_count=0,
            offset=0, limit=1,
            warnings=[RetrievalWarning(code="DOCUMENT_NOT_FOUND", message=f"Document {document_id} not found")],
        )

    children = [ko for ko in all_objects.values() if ko.parent_id == document_id]
    tree = assemble_hierarchy(doc, children)

    return RetrievalResult(
        objects=tree,
        total_count=len(tree),
        returned_count=len(tree),
        offset=0,
        limit=len(tree),
    )
