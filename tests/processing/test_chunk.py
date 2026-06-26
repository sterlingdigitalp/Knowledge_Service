"""Tests for Chunk stage"""

import pytest
from src.knowledge_service.processing.chunk import ChunkStage
from src.knowledge_service.processing.context import ProcessingContext
from src.knowledge_service.knowledge_object import KnowledgeObject


class TestChunkStage:

    def test_does_not_chunk_small_content(self):
        ctx = ProcessingContext()
        ctx.markdown = "Short content."
        ctx.word_count = 3
        ctx.knowledge_objects = [KnowledgeObject(id="parent-1")]
        stage = ChunkStage()
        ctx = stage.execute(ctx, {"strategy": "semantic", "min_chunk_size_tokens": 50})
        assert len(ctx.chunks) == 0

    def test_semantic_chunk_by_headings(self):
        md = "# Section 1\n\nContent for section 1.\n\n## Subsection\n\nMore content.\n\n# Section 2\n\nFinal section."
        ctx = ProcessingContext()
        ctx.markdown = md
        ctx.word_count = len(md.split())
        ctx.knowledge_objects = [KnowledgeObject(id="parent-1")]
        stage = ChunkStage()
        ctx = stage.execute(ctx, {"strategy": "semantic", "min_chunk_size_tokens": 3})
        assert len(ctx.chunks) > 1

    def test_chunks_have_required_fields(self):
        md = "# First\n\nContent.\n\n# Second\n\nMore."
        ctx = ProcessingContext()
        ctx.markdown = md
        ctx.word_count = len(md.split())
        ctx.knowledge_objects = [KnowledgeObject(id="parent-1")]
        stage = ChunkStage()
        ctx = stage.execute(ctx, {"strategy": "semantic"})
        for c in ctx.chunks:
            assert "parent_id" in c
            assert "chunk_index" in c
            assert "chunk_total" in c
            assert "content" in c
            assert "content_hash" in c

    def test_chunk_indexes_are_sequential(self):
        md = "# A\n\nX\n\n# B\n\nY\n\n# C\n\nZ"
        ctx = ProcessingContext()
        ctx.markdown = md
        ctx.word_count = len(md.split())
        ctx.knowledge_objects = [KnowledgeObject(id="parent-1")]
        stage = ChunkStage()
        ctx = stage.execute(ctx, {"strategy": "semantic"})
        for i, c in enumerate(ctx.chunks):
            assert c["chunk_index"] == i
        if ctx.chunks:
            assert ctx.chunks[0]["chunk_total"] == len(ctx.chunks)

    def test_chunk_determinism(self):
        md = "# A\n\nX\n\n# B\n\nY"
        ctx1 = ProcessingContext()
        ctx1.markdown = md
        ctx1.word_count = len(md.split())
        ctx1.knowledge_objects = [KnowledgeObject(id="parent-1")]
        stage = ChunkStage()
        ctx1 = stage.execute(ctx1, {"strategy": "semantic"})

        ctx2 = ProcessingContext()
        ctx2.markdown = md
        ctx2.word_count = len(md.split())
        ctx2.knowledge_objects = [KnowledgeObject(id="parent-1")]
        ctx2 = stage.execute(ctx2, {"strategy": "semantic"})

        assert len(ctx1.chunks) == len(ctx2.chunks)
        for c1, c2 in zip(ctx1.chunks, ctx2.chunks):
            assert c1["content"] == c2["content"]
            assert c1["content_hash"] == c2["content_hash"]

    def test_fixed_size_chunking(self):
        md = "word " * 200
        ctx = ProcessingContext()
        ctx.markdown = md
        ctx.word_count = 200
        ctx.knowledge_objects = [KnowledgeObject(id="parent-1")]
        stage = ChunkStage()
        ctx = stage.execute(ctx, {"strategy": "fixed_size", "chunk_size_tokens": 50})
        assert len(ctx.chunks) >= 3

    def test_empty_content(self):
        ctx = ProcessingContext()
        ctx.markdown = ""
        ctx.word_count = 0
        ctx.knowledge_objects = [KnowledgeObject(id="parent-1")]
        stage = ChunkStage()
        ctx = stage.execute(ctx, {})
        assert "warnings" in str(ctx.stage_results.get("chunk"))
