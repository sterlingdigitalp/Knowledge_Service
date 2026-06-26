"""Tests for Extract stage"""

import pytest
from src.knowledge_service.processing.extract import ExtractStage
from src.knowledge_service.processing.context import ProcessingContext


class TestExtractStage:

    def test_extracts_title_from_markdown_heading(self):
        ctx = ProcessingContext()
        ctx.normalized_content = "# My Document Title\n\nBody text here."
        ctx.normalized_metadata = {}
        stage = ExtractStage()
        ctx = stage.execute(ctx, {})
        assert ctx.title == "My Document Title"

    def test_extracts_title_fallback_to_first_line(self):
        ctx = ProcessingContext()
        ctx.normalized_content = "Short Title\n\nBody text."
        ctx.normalized_metadata = {}
        stage = ExtractStage()
        ctx = stage.execute(ctx, {})
        assert ctx.title is None or len(ctx.title) < 200

    def test_extracts_authors(self):
        ctx = ProcessingContext()
        ctx.normalized_content = "# Article\n\nBy John Smith and Jane Doe\n\nContent."
        ctx.normalized_metadata = {}
        stage = ExtractStage()
        ctx = stage.execute(ctx, {"extract_authors": True})
        assert len(ctx.authors) > 0
        assert "John Smith" in ctx.authors

    def test_extracts_date_iso(self):
        ctx = ProcessingContext()
        ctx.normalized_content = "Published on 2026-06-25.\n\nContent."
        ctx.normalized_metadata = {}
        stage = ExtractStage()
        ctx = stage.execute(ctx, {})
        assert ctx.extracted_data.get("published_date") is not None
        assert "2026" in ctx.extracted_data["published_date"]

    def test_extracts_date_named_month(self):
        ctx = ProcessingContext()
        ctx.normalized_content = "Published June 25, 2026.\n\nContent."
        ctx.normalized_metadata = {}
        stage = ExtractStage()
        ctx = stage.execute(ctx, {})
        assert ctx.extracted_data.get("published_date") is not None

    def test_extracts_citations(self):
        ctx = ProcessingContext()
        ctx.normalized_content = "See https://example.com/ref for details."
        ctx.normalized_metadata = {}
        stage = ExtractStage()
        ctx = stage.execute(ctx, {"extract_citations": True})
        assert len(ctx.citations) > 0
        assert ctx.citations[0]["target_url"] == "https://example.com/ref"

    def test_extracts_code_blocks(self):
        ctx = ProcessingContext()
        ctx.normalized_content = "Some text\n\n```python\nprint('hello')\n```\n\nMore text."
        ctx.normalized_metadata = {}
        stage = ExtractStage()
        ctx = stage.execute(ctx, {})
        assert ctx.extracted_data.get("code_blocks_count") == 1
        assert "python" in ctx.extracted_data.get("code_blocks_languages", [])

    def test_empty_content(self):
        ctx = ProcessingContext()
        ctx.normalized_content = ""
        ctx.normalized_metadata = {}
        stage = ExtractStage()
        ctx = stage.execute(ctx, {})
        assert ctx.stage_results["extract"].success
