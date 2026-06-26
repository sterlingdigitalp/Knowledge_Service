"""Crawl4AI Provider Contract Tests — HF-001

Verifies that ProviderResponse.content is always str | None
regardless of upstream Crawl4AI API schema version.
"""

import os, sys
_SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'src'))
sys.path.insert(0, _SRC_PATH)
sys.path.insert(0, os.path.dirname(_SRC_PATH))

import pytest
from copy import deepcopy
from unittest.mock import patch, MagicMock
from knowledge_service.providers.crawl4ai_provider import Crawl4AIProvider
from knowledge_service.interfaces.provider import ProviderRequest, ProviderType, ProviderResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_response(status_code: int, json_data: dict):
    mock = MagicMock()
    mock.status_code = status_code
    mock.is_success = status_code < 400
    mock.json.return_value = json_data
    return mock


BASE_SUCCESS_JSON = {
    "success": True,
    "results": [{
        "success": True,
        "url": "https://example.com",
        "status_code": 200,
        "metadata": {"title": "Example"},
    }],
}


def _execute_with_mock(provider, mock_response, target="https://example.com"):
    with patch("httpx.post", return_value=mock_response):
        return provider.execute(ProviderRequest(
            target=target, provider_type=ProviderType.CRAWL,
        ))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def provider():
    p = Crawl4AIProvider("crawl4ai-test")
    p._config = {"endpoint": "http://localhost:11235", "auth_token": "test", "timeout_ms": 30000}
    p._is_initialized = True
    p._version = "0.9.0"
    return p


# ---------------------------------------------------------------------------
# Contract: content is ALWAYS str | None
# ---------------------------------------------------------------------------

class TestCrawl4AIContract:

    def test_legacy_string_markdown(self, provider):
        """Legacy Crawl4AI: markdown is a plain string."""
        json_data = deepcopy(BASE_SUCCESS_JSON)
        json_data["results"][0]["markdown"] = "# Hello\n\nWorld."
        json_data["results"][0]["html"] = "<html><body><h1>Hello</h1><p>World.</p></body></html>"

        resp = _execute_with_mock(provider, _make_mock_response(200, json_data))
        assert isinstance(resp.content, str)
        assert resp.content == "# Hello\n\nWorld."
        assert resp.content_type == "text/markdown"

    def test_new_dict_markdown(self, provider):
        """Current Crawl4AI v0.4+: markdown is a dict with sub-keys.

        Provider must extract raw_markdown -> markdown_with_citations -> fit_markdown.
        """
        json_data = deepcopy(BASE_SUCCESS_JSON)
        json_data["results"][0]["markdown"] = {
            "raw_markdown": "# Example Domain\n\nContent.",
            "markdown_with_citations": "# Example Domain\n\nContent.\n",
            "references_markdown": "\n## References\n",
            "fit_markdown": "",
            "fit_html": "",
        }

        resp = _execute_with_mock(provider, _make_mock_response(200, json_data))
        assert isinstance(resp.content, str), f"Expected str, got {type(resp.content)}"
        assert "Example Domain" in resp.content
        assert resp.content_type == "text/markdown"

    def test_dict_markdown_fallback_precedence(self, provider):
        """When raw_markdown is empty, fall back to markdown_with_citations."""
        json_data = deepcopy(BASE_SUCCESS_JSON)
        json_data["results"][0]["markdown"] = {
            "raw_markdown": "",
            "markdown_with_citations": "# Citations\n\nCited content.",
            "references_markdown": "\n## References\n",
            "fit_markdown": "",
            "fit_html": "",
        }

        resp = _execute_with_mock(provider, _make_mock_response(200, json_data))
        assert isinstance(resp.content, str)
        assert resp.content == "# Citations\n\nCited content."

    def test_dict_markdown_all_empty_falls_to_html(self, provider):
        """When all markdown sub-keys are empty, fall back to html."""
        json_data = deepcopy(BASE_SUCCESS_JSON)
        json_data["results"][0]["markdown"] = {
            "raw_markdown": "", "markdown_with_citations": "",
            "references_markdown": "", "fit_markdown": "", "fit_html": "",
        }
        json_data["results"][0]["html"] = "<html><body><h1>HTML fallback</h1></body></html>"

        resp = _execute_with_mock(provider, _make_mock_response(200, json_data))
        assert isinstance(resp.content, str)
        assert resp.content == "<html><body><h1>HTML fallback</h1></body></html>"
        assert resp.content_type == "text/html"

    def test_no_markdown_falls_to_extracted_content(self, provider):
        """No markdown key at all -> fall through to extracted_content."""
        json_data = deepcopy(BASE_SUCCESS_JSON)
        json_data["results"][0].pop("markdown", None)
        json_data["results"][0]["html"] = ""
        json_data["results"][0]["extracted_content"] = "Extracted plain text."

        resp = _execute_with_mock(provider, _make_mock_response(200, json_data))
        assert isinstance(resp.content, str)
        assert resp.content == "Extracted plain text."
        assert resp.content_type == "text/plain"

    def test_empty_response_returns_empty_string(self, provider):
        """No content fields at all -> empty string."""
        json_data = deepcopy(BASE_SUCCESS_JSON)
        json_data["results"][0].pop("markdown", None)
        json_data["results"][0].pop("html", None)
        json_data["results"][0].pop("extracted_content", None)

        resp = _execute_with_mock(provider, _make_mock_response(200, json_data))
        assert isinstance(resp.content, str)
        assert resp.content == ""

    def test_markdown_is_nonstandard_type(self, provider):
        """markdown field is neither str nor dict -> treat as empty."""
        json_data = deepcopy(BASE_SUCCESS_JSON)
        json_data["results"][0]["markdown"] = 42
        json_data["results"][0]["html"] = "<html><body>Number fallback</body></html>"

        resp = _execute_with_mock(provider, _make_mock_response(200, json_data))
        assert isinstance(resp.content, str)
        assert resp.content == "<html><body>Number fallback</body></html>"

    def test_error_response_content_is_none(self, provider):
        """On error, content defaults to None (not a dict)."""
        json_data = deepcopy(BASE_SUCCESS_JSON)
        json_data["results"][0]["success"] = False
        json_data["results"][0]["error_message"] = "Server error"

        resp = _execute_with_mock(provider, _make_mock_response(200, json_data))
        assert resp.error is not None
        assert resp.content is None

    def test_dict_markdown_raw_markdown_missing_key(self, provider):
        """raw_markdown key absent from dict -> fall through chain."""
        json_data = deepcopy(BASE_SUCCESS_JSON)
        json_data["results"][0]["markdown"] = {
            "markdown_with_citations": "# Citations\n\nCited.",
            "fit_markdown": "",
            "fit_html": "",
        }

        resp = _execute_with_mock(provider, _make_mock_response(200, json_data))
        assert isinstance(resp.content, str)
        assert resp.content == "# Citations\n\nCited."
