"""SearXNG Search Provider - Verified Implementation (Phase 1.1C)

Contract derived from live infrastructure interrogation:
- Search: GET /search?q=<query>&format=json
- Verified response fields: query, results[{url, title, content, engine, score, category, template, publishedDate, thumbnail, engines, positions, parsed_url}], answers, corrections, infoboxes, suggestions, unresponsive_engines
- Health: GET /search?q=test&format=json -> HTTP 200 with valid JSON
- Version: from HTML <meta name="generator" content="searxng-2026.6.22+75c1b1dad">
"""

import httpx
import re
from typing import Dict, Any, Optional
from ..interfaces.provider import Provider, ProviderRequest, ProviderResponse, ProviderError, InitResult, HealthCheckResult, HealthStatus, ProviderType


SEARXNG_VERSION_PATTERN = re.compile(r'searxng-([\d.]+(?:\+[a-f0-9]+)?)')


class SearXNGSearchProvider(Provider):
    """SearXNG search provider — verified against live infrastructure at http://localhost:8080"""
    
    def __init__(self, name: str = "searxng-main"):
        self._name = name
        self._config: Dict[str, Any] = {}
        self._is_initialized = False
        self._version: Optional[str] = None
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def capabilities(self) -> Dict[str, Any]:
        return {
            "can_crawl": False,
            "can_search": True,
            "can_fetch_api": False,
            "can_read_rss": False,
            "can_process_files": False,
            "can_query_database": False,
            "supported_content_types": ["text/html", "application/json"],
            "version": self._version or "unknown",
            "max_results": 19,
            "supported_languages": True,
            "supported_categories": True,
            "supported_engines": True
        }
    
    def initialize(self, config: Dict[str, Any]) -> InitResult:
        """Initialize SearXNG provider with configuration, discover version"""
        self._config = config
        
        # Verify health and discover version during initialization
        health_result = self.health()
        if health_result.status == HealthStatus.UNHEALTHY:
            raise RuntimeError(
                f"SearXNG provider initialization failed: {health_result.degradation_reason}"
            )
        
        # Discover version from root HTML meta generator tag
        base_url = self._config.get("endpoint", "http://localhost:8080")
        try:
            resp = httpx.get(base_url, timeout=5.0)
            if resp.status_code == 200:
                m = SEARXNG_VERSION_PATTERN.search(resp.text)
                if m:
                    self._version = m.group(1)
        except Exception:
            self._version = "unknown"
        
        self._is_initialized = True
        
        return InitResult(
            name=self._name,
            version=self._version or "unknown",
            capabilities=self.capabilities
        )
    
    def execute(self, request: ProviderRequest) -> ProviderResponse:
        """Execute search query against SearXNG API — GET /search?q=<query>&format=json"""
        if not self._is_initialized:
            raise RuntimeError("SearXNG provider not initialized")
        
        base_url = self._config.get("endpoint", "http://localhost:8080")
        
        # Verified query parameters
        params = {
            "q": request.target,
            "format": "json"
        }
        
        # Add optional parameters from request options
        if "engines" in request.options:
            params["engines"] = request.options["engines"]
        if "language" in request.options:
            params["language"] = request.options["language"]
        if "categories" in request.options:
            params["categories"] = request.options["categories"]
        if "pageno" in request.options:
            params["pageno"] = request.options["pageno"]
        
        try:
            response = httpx.get(
                f"{base_url}/search",
                params=params,
                timeout=self._config.get("timeout_ms", 15000) / 1000.0
            )
            
            if not response.is_success:
                return ProviderResponse(
                    error=ProviderError(
                        code="SERVER_ERROR" if response.status_code >= 500 else "NETWORK_ERROR",
                        message=f"SearXNG returned status {response.status_code}",
                        provider_specific_code=str(response.status_code),
                        retryable=response.status_code >= 500,
                        recoverable=True
                    )
                )
            
            # Parse and return full verified response structure
            result = response.json()
            
            search_results = result.get("results", [])
            
            # Normalize results to structured format for Processing Layer
            normalized_results = []
            for res in search_results:
                normalized_results.append({
                    "url": res.get("url"),
                    "title": res.get("title"),
                    "content": res.get("content"),
                    "engine": res.get("engine"),
                    "score": res.get("score", 0.0),
                    "category": res.get("category", "general"),
                    "published_date": res.get("publishedDate"),
                    "thumbnail": res.get("thumbnail"),
                    "template": res.get("template"),
                    "parsed_url": res.get("parsed_url"),
                })
            
            return ProviderResponse(
                content=None,
                content_type="application/json",
                status_code=response.status_code,
                metadata={
                    "query": result.get("query"),
                    "results": normalized_results,
                    "suggestions": result.get("suggestions", []),
                    "answers": result.get("answers", []),
                    "infoboxes": result.get("infoboxes", []),
                    "corrections": result.get("corrections", []),
                    "unresponsive_engines": result.get("unresponsive_engines", []),
                }
            )
            
        except httpx.TimeoutException:
            return ProviderResponse(
                error=ProviderError(
                    code="TIMEOUT",
                    message="SearXNG search request timed out",
                    retryable=True,
                    recoverable=True
                )
            )
        except httpx.HTTPStatusError as e:
            return ProviderResponse(
                error=ProviderError(
                    code="SERVER_ERROR" if e.response.status_code >= 500 else "NETWORK_ERROR",
                    message=f"SearXNG HTTP error: {e.response.status_code}",
                    provider_specific_code=str(e.response.status_code),
                    retryable=e.response.status_code >= 500,
                    recoverable=True
                )
            )
        except Exception as e:
            return ProviderResponse(
                error=ProviderError(
                    code="INVALID_RESPONSE",
                    message=f"SearXNG invalid response: {str(e)}",
                    retryable=False,
                    recoverable=True
                )
            )
    
    def health(self) -> HealthCheckResult:
        """Check SearXNG service health via search endpoint"""
        base_url = self._config.get("endpoint", "http://localhost:8080")
        
        try:
            response = httpx.get(
                f"{base_url}/search",
                params={"q": "test", "format": "json"},
                timeout=5.0
            )
            
            if response.status_code == 200:
                result = response.json()
                if "query" in result and "results" in result:
                    return HealthCheckResult(status=HealthStatus.HEALTHY)
                else:
                    return HealthCheckResult(
                        status=HealthStatus.DEGRADED,
                        degradation_reason="Invalid response structure"
                    )
            elif response.status_code == 503:
                return HealthCheckResult(status=HealthStatus.UNHEALTHY, degradation_reason="Service unavailable")
            else:
                return HealthCheckResult(
                    status=HealthStatus.DEGRADED,
                    degradation_reason=f"Unexpected status {response.status_code}"
                )
        except Exception:
            return HealthCheckResult(status=HealthStatus.UNHEALTHY, degradation_reason="Connection failed")
    
    def shutdown(self) -> None:
        """Shutdown SearXNG provider"""
        self._is_initialized = False
