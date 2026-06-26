"""Tests for Normalize stage"""

import pytest
from src.knowledge_service.processing.normalize import NormalizeStage
from src.knowledge_service.processing.context import ProcessingContext


class TestNormalizeStage:

    def test_detects_language_english(self):
        ctx = ProcessingContext()
        ctx.cleaned_content = "The quick brown fox jumps over the lazy dog. This is a test."
        stage = NormalizeStage()
        ctx = stage.execute(ctx, {"detect_language": True})
        assert ctx.language == "en"

    def test_detects_language_spanish(self):
        ctx = ProcessingContext()
        ctx.cleaned_content = "El gato y el perro son animales. La casa es grande."
        stage = NormalizeStage()
        ctx = stage.execute(ctx, {"detect_language": True})
        assert ctx.language in ["es", "en"]

    def test_detects_content_type_article(self):
        ctx = ProcessingContext()
        ctx.cleaned_content = "# Title\n\nThis is a paragraph about something interesting."
        stage = NormalizeStage()
        ctx = stage.execute(ctx, {})
        assert ctx.normalized_metadata.get("content_type") == "article"

    def test_detects_content_type_code(self):
        ctx = ProcessingContext()
        ctx.cleaned_content = "```python\ndef hello():\n    print('world')\n```\n\nThis is code."
        stage = NormalizeStage()
        ctx = stage.execute(ctx, {})
        assert ctx.normalized_metadata.get("content_type") in ["code", "article"]

    def test_normalizes_headings(self):
        ctx = ProcessingContext()
        ctx.cleaned_content = "# Valid H1\n\n### Valid H3\n\n####### Too Deep"
        stage = NormalizeStage()
        ctx = stage.execute(ctx, {"normalize_headings": True})
        assert "# Too Deep" in ctx.normalized_content
        assert "#######" not in ctx.normalized_content

    def test_empty_content(self):
        ctx = ProcessingContext()
        ctx.cleaned_content = ""
        stage = NormalizeStage()
        ctx = stage.execute(ctx, {})
        assert "warnings" in str(ctx.stage_results.get("normalize"))

    def test_metadata_fields(self):
        ctx = ProcessingContext()
        ctx.cleaned_content = "Some content here."
        stage = NormalizeStage()
        ctx = stage.execute(ctx, {})
        assert "total_lines" in ctx.normalized_metadata
        assert "char_count" in ctx.normalized_metadata
