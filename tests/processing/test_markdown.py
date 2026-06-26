"""Tests for Markdown stage"""

import pytest
from src.knowledge_service.processing.markdown import MarkdownStage
from src.knowledge_service.processing.context import ProcessingContext


class TestMarkdownStage:

    def test_converts_to_markdown(self):
        ctx = ProcessingContext()
        ctx.raw_content = "Raw content"
        ctx.cleaned_content = "Hello World"
        ctx.normalized_content = "Hello World"
        stage = MarkdownStage()
        ctx = stage.execute(ctx, {})
        assert "Hello World" in ctx.markdown

    def test_preserves_heading_hierarchy(self):
        ctx = ProcessingContext()
        ctx.raw_content = "raw"
        ctx.cleaned_content = "# H1\n\n## H2\n\n### H3"
        ctx.normalized_content = "# H1\n\n## H2\n\n### H3"
        stage = MarkdownStage()
        ctx = stage.execute(ctx, {})
        assert "# H1" in ctx.markdown
        assert "## H2" in ctx.markdown
        assert "### H3" in ctx.markdown

    def test_preserves_code_blocks(self):
        ctx = ProcessingContext()
        ctx.raw_content = "raw"
        ctx.cleaned_content = "Text\n\n```python\nprint('hello')\n```\n\nEnd"
        ctx.normalized_content = "Text\n\n```python\nprint('hello')\n```\n\nEnd"
        stage = MarkdownStage()
        ctx = stage.execute(ctx, {"preserve_code_formatting": True})
        assert "```python" in ctx.markdown
        assert "print('hello')" in ctx.markdown

    def test_generates_content_hash(self):
        ctx = ProcessingContext()
        ctx.raw_content = "Raw test content"
        ctx.cleaned_content = "# Hello\n\nWorld."
        ctx.normalized_content = "# Hello\n\nWorld."
        stage = MarkdownStage()
        ctx = stage.execute(ctx, {})
        assert ctx.content_hash is not None
        assert len(ctx.content_hash) == 64

    def test_generates_raw_content_hash(self):
        ctx = ProcessingContext()
        ctx.raw_content = "Raw test content"
        ctx.cleaned_content = "Hello"
        ctx.normalized_content = "Hello"
        stage = MarkdownStage()
        ctx = stage.execute(ctx, {})
        assert ctx.raw_content_hash is not None
        assert len(ctx.raw_content_hash) == 64

    def test_hash_determinism(self):
        ctx1 = ProcessingContext()
        ctx1.raw_content = "same raw"
        ctx1.cleaned_content = "Same content"
        ctx1.normalized_content = "Same content"
        stage = MarkdownStage()
        ctx1 = stage.execute(ctx1, {})

        ctx2 = ProcessingContext()
        ctx2.raw_content = "same raw"
        ctx2.cleaned_content = "Same content"
        ctx2.normalized_content = "Same content"
        ctx2 = stage.execute(ctx2, {})

        assert ctx1.content_hash == ctx2.content_hash
        assert ctx1.raw_content_hash == ctx2.raw_content_hash

    def test_computes_word_count(self):
        ctx = ProcessingContext()
        ctx.raw_content = "raw"
        ctx.cleaned_content = "One two three four five"
        ctx.normalized_content = "One two three four five"
        stage = MarkdownStage()
        ctx = stage.execute(ctx, {})
        assert ctx.word_count == 5

    def test_empty_content(self):
        ctx = ProcessingContext()
        ctx.raw_content = ""
        ctx.cleaned_content = ""
        ctx.normalized_content = ""
        stage = MarkdownStage()
        ctx = stage.execute(ctx, {})
        assert "warnings" in str(ctx.stage_results.get("markdown"))
