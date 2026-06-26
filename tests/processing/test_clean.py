"""Tests for Clean stage"""

import pytest
from src.knowledge_service.processing.clean import CleanStage
from src.knowledge_service.processing.context import ProcessingContext


class TestCleanStage:

    def setup(self, content="", bundle=None):
        ctx = ProcessingContext()
        ctx.raw_content = content
        return ctx

    def test_strips_html_tags(self):
        ctx = self.setup(content="<html><body><p>Hello <b>World</b></p></body></html>")
        stage = CleanStage()
        ctx = stage.execute(ctx, {})
        assert "Hello World" in ctx.cleaned_content
        assert "<html>" not in ctx.cleaned_content
        assert "<b>" not in ctx.cleaned_content

    def test_removes_scripts(self):
        ctx = self.setup(content="<script>alert('xss')</script>Hello")
        stage = CleanStage()
        ctx = stage.execute(ctx, {"strip_scripts": True})
        assert "Hello" in ctx.cleaned_content
        assert "script" not in ctx.cleaned_content

    def test_removes_styles(self):
        ctx = self.setup(content="<style>body { color: red; }</style>Hello")
        stage = CleanStage()
        ctx = stage.execute(ctx, {"strip_scripts": True})
        assert "Hello" in ctx.cleaned_content
        assert "color: red" not in ctx.cleaned_content

    def test_removes_comments(self):
        ctx = self.setup(content="Hello<!-- comment -->World")
        stage = CleanStage()
        ctx = stage.execute(ctx, {})
        assert "HelloWorld" in ctx.cleaned_content

    def test_normalizes_whitespace(self):
        ctx = self.setup(content="Hello   World\n\n\n\nEnd")
        stage = CleanStage()
        ctx = stage.execute(ctx, {"normalize_whitespace": True})
        assert "Hello World" in ctx.cleaned_content
        assert "\n\n\n" not in ctx.cleaned_content

    def test_decodes_html_entities(self):
        ctx = self.setup(content="&amp; &lt; &gt; &quot; &#39;")
        stage = CleanStage()
        ctx = stage.execute(ctx, {})
        assert "&" in ctx.cleaned_content
        assert "&amp;" not in ctx.cleaned_content

    def test_empty_content(self):
        ctx = self.setup(content="")
        stage = CleanStage()
        ctx = stage.execute(ctx, {})
        assert ctx.cleaned_content == ""

    def test_content_without_html(self):
        ctx = self.setup(content="Plain text content\n\nSecond paragraph.")
        stage = CleanStage()
        ctx = stage.execute(ctx, {})
        assert ctx.cleaned_content == "Plain text content\n\nSecond paragraph."

    def test_truncates_large_content(self):
        large = "a" * (20 * 1024 * 1024)
        ctx = self.setup(content=large)
        stage = CleanStage()
        ctx = stage.execute(ctx, {"max_content_length": 1024})
        assert len(ctx.cleaned_content.encode("utf-8")) <= 2048

    def test_removes_navigation_elements(self):
        ctx = self.setup(content="<nav>Menu</nav>Content<footer>Footer</footer>")
        stage = CleanStage()
        ctx = stage.execute(ctx, {"strip_navigation": True})
        assert "Content" in ctx.cleaned_content
        assert "Menu" not in ctx.cleaned_content
        assert "Footer" not in ctx.cleaned_content
