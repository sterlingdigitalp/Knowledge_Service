"""Stage 7: Validate — required fields, hashes, chunk relationships, confidence bounds, schema

Input: enriched context
Output: Knowledge Objects marked as validated, warnings for non-fatal issues,
        rejection for fatal issues
"""

from typing import Dict, Any, List
from .context import ProcessingContext, StageResult
from ..knowledge_object import KnowledgeObject


class ValidationError(Exception):
    pass


class ValidateStage:

    def execute(self, context: ProcessingContext, config: Dict[str, Any]) -> ProcessingContext:
        if not context.knowledge_objects:
            context.stage_results["validate"] = StageResult("validate", False, confidence_impact=-0.05, error="No Knowledge Objects to validate")
            return context

        rejected: List[str] = []

        for ko in context.knowledge_objects:
            result = self._validate_single(ko, context, config)
            if result == "rejected":
                rejected.append(ko.id)
            elif result == "warning":
                context.warnings.append(f"Validation warning for {ko.id}")

        if rejected:
            context.knowledge_objects = [ko for ko in context.knowledge_objects if ko.id not in rejected]
            if rejected:
                context.warnings.append(f"Rejected {len(rejected)} Knowledge Objects")

        if context.chunks:
            chunk_ids = [c.get("content_hash", "") for c in context.chunks]
            for chunk in context.chunks:
                if chunk.get("parent_id") and chunk["parent_id"] not in [ko.id for ko in context.knowledge_objects]:
                    context.warnings.append(f"Chunk {chunk.get('chunk_index')} parent_id not found in knowledge objects")
                if chunk.get("content_hash") and chunk["content_hash"] not in chunk_ids:
                    context.warnings.append(f"Chunk {chunk.get('chunk_index')} content_hash integrity check")

        context.stage_results["validate"] = StageResult("validate", True, confidence_impact=0.0)
        return context

    def _validate_single(self, ko: KnowledgeObject, context: ProcessingContext, config: Dict[str, Any]) -> str:
        errors: List[str] = []
        warnings: List[str] = []

        if not ko.id:
            errors.append("Missing id")
        if ko.confidence < 0.0 or ko.confidence > 1.0:
            errors.append(f"Confidence {ko.confidence} out of range [0.0, 1.0]")
        if not ko.raw_content_hash:
            errors.append("Missing raw_content_hash")
        if not ko.content_hash:
            errors.append("Missing content_hash")
        if not ko.source_id:
            errors.append("Missing source_id")
        if not ko.acquired_at:
            errors.append("Missing acquired_at")
        if not ko.updated_at:
            errors.append("Missing updated_at")
        if not ko.acquisition_chain:
            warnings.append("Empty acquisition_chain")
        if not ko.source_url and ko.source_type.value != "other":
            warnings.append("Missing source_url for non-other source type")
        if ko.type.value == "document" and not ko.markdown:
            warnings.append("Document type without markdown content")
        if ko.type.value == "chunk":
            if ko.parent_id is None:
                errors.append("Chunk type missing parent_id")
            if ko.chunk_index is None:
                errors.append("Chunk type missing chunk_index")
            if ko.chunk_total is None:
                errors.append("Chunk type missing chunk_total")

        computed_raw = KnowledgeObject.compute_raw_content_hash(
            context.raw_content.encode("utf-8")
        )
        if ko.raw_content_hash != computed_raw:
            errors.append("raw_content_hash mismatch")

        if ko.markdown:
            computed_content = KnowledgeObject.compute_content_hash(ko.markdown)
            if ko.content_hash != computed_content:
                errors.append("content_hash mismatch")

        if errors:
            return "rejected"
        if warnings:
            return "warning"
        return "passed"
