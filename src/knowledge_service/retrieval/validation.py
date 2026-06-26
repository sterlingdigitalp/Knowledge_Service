"""Retrieval Validation — Verify retrieved Knowledge Objects are uncorrupted"""

from typing import Optional, List
from ..knowledge_object import KnowledgeObject
from .interfaces import RetrievalWarning


class RetrievalValidator:
    """Validates that retrieved Knowledge Objects are complete and uncorrupted."""

    @staticmethod
    def validate(ko: KnowledgeObject) -> List[RetrievalWarning]:
        warnings: List[RetrievalWarning] = []

        if not ko.id:
            warnings.append(RetrievalWarning(
                code="MISSING_ID", message="Knowledge Object has no ID", object_id=ko.id
            ))

        if not ko.content_hash:
            warnings.append(RetrievalWarning(
                code="MISSING_CONTENT_HASH", message="Object has no content hash", object_id=ko.id
            ))
        else:
            computed = KnowledgeObject.compute_content_hash(ko.markdown or "")
            if computed != ko.content_hash:
                warnings.append(RetrievalWarning(
                    code="CONTENT_HASH_MISMATCH",
                    message=f"Content hash mismatch: stored={ko.content_hash}, computed={computed}",
                    object_id=ko.id,
                ))

        if not isinstance(ko.confidence, (int, float)) or ko.confidence < 0.0 or ko.confidence > 1.0:
            warnings.append(RetrievalWarning(
                code="INVALID_CONFIDENCE",
                message=f"Confidence out of range [0,1]: {ko.confidence}",
                object_id=ko.id,
            ))

        if ko.version < 1:
            warnings.append(RetrievalWarning(
                code="INVALID_VERSION",
                message=f"Version must be >= 1: {ko.version}",
                object_id=ko.id,
            ))

        if ko.chunk_index is not None and ko.chunk_total is not None:
            if ko.chunk_index < 0:
                warnings.append(RetrievalWarning(
                    code="INVALID_CHUNK_INDEX",
                    message=f"Negative chunk index: {ko.chunk_index}",
                    object_id=ko.id,
                ))
            if ko.chunk_total < 1:
                warnings.append(RetrievalWarning(
                    code="INVALID_CHUNK_TOTAL",
                    message=f"Invalid chunk total: {ko.chunk_total}",
                    object_id=ko.id,
                ))
            if ko.chunk_index >= ko.chunk_total:
                warnings.append(RetrievalWarning(
                    code="CHUNK_INDEX_OUT_OF_RANGE",
                    message=f"Chunk index {ko.chunk_index} >= total {ko.chunk_total}",
                    object_id=ko.id,
                ))

        if not ko.acquired_at:
            warnings.append(RetrievalWarning(
                code="MISSING_ACQUIRED_AT",
                message="Object has no acquisition timestamp",
                object_id=ko.id,
            ))

        for i, record in enumerate(ko.acquisition_chain):
            if not record.provider_name:
                warnings.append(RetrievalWarning(
                    code="MISSING_PROVIDER_IN_CHAIN",
                    message=f"Acquisition chain entry {i} has no provider name",
                    object_id=ko.id,
                ))

        return warnings
