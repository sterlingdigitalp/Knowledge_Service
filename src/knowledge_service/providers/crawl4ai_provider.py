"""Crawl4AI Provider - Verified Implementation (Phase 1.1C)

Contract derived from live infrastructure interrogation:
- OpenAPI spec at http://localhost:11235/openapi.json
- Health: GET /health -> {"status": "ok", "version": "0.9.0", ...}
- Crawl: POST /crawl with {"urls": ["https://..."]} -> {"success": true, "results": [{url, markdown, html, metadata, links, ...}]}
- Markdown: POST /md with {"url": "https://...", "f": "raw"} -> {"markdown": "...", "success": true}
- Auth: Bearer token in Authorization header (token from CRAWL4AI_API_TOKEN env)
"""

import httpx
import re
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from ..interfaces.provider import Provider, ProviderRequest, ProviderResponse, ProviderError, InitResult, HealthCheckResult, HealthStatus, ProviderType


CRAWL4AI_VERSION_PATTERN = re.compile(r'(\d+\.\d+\.\d+)')


class Crawl4AIProvider(Provider):
    """Crawl4AI provider - verified against live infrastructure at http://localhost:11235"""
    
    def __init__(self, name: str = "crawl4ai-primary"):
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
            "can_crawl": True,
            "can_search": False,
            "can_fetch_api": False,
            "can_read_rss": False,
            "can_process_files": False,
            "can_query_database": False,
            "supported_content_types": ["text/html", "text/markdown", "application/xhtml+xml"],
            "max_depth": 1,
            "version": self._version or "unknown",
            "endpoints": ["health", "crawl", "markdown", "html", "screenshot", "pdf", "execute_js"]
        }
    
    def initialize(self, config: Dict[str, Any]) -> InitResult:
        """Initialize from configuration, discover version via health check"""
        self._config = config
        
        auth_token = (config.get("credentials") or {}).get("auth_token") or config.get("auth_token")
        if not auth_token:
            raise ValueError("Crawl4AI provider requires authentication token in config")
        self._config["auth_token"] = auth_token
        
        # Discover version and verify health by interrogating /health endpoint
        health_result = self.health()
        if health_result.status == HealthStatus.UNHEALTHY:
            raise RuntimeError(
                f"Crawl4AI provider initialization failed: {health_result.degradation_reason}"
            )
        
        # Discover version from health response
        base_url = self._config.get("endpoint", "http://localhost:11235")
        try:
            resp = httpx.get(
                f"{base_url}/health",
                headers={"Authorization": f"Bearer {auth_token}"},
                timeout=5.0
            )
            if resp.status_code == 200:
                body = resp.json()
                version_str = body.get("version", "")
                m = CRAWL4AI_VERSION_PATTERN.search(version_str)
                if m:
                    self._version = m.group(1)
                else:
                    self._version = version_str or "0.9.0"
        except Exception:
            self._version = "0.9.0"
        
        self._is_initialized = True
        
        return InitResult(
            name=self._name,
            version=self._version or "0.9.0",
            capabilities=self.capabilities
        )
    
    def execute(self, request: ProviderRequest) -> ProviderResponse:
        """Execute crawl request via POST /crawl (synchronous) - verified contract"""
        if not self._is_initialized:
            raise RuntimeError("Crawl4AI provider not initialized")
        
        auth_token = self._config.get("auth_token")
        base_url = self._config.get("endpoint", "http://localhost:11235")
        timeout_s = self._config.get("timeout_ms", 60000) / 1000.0
        
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        # Verified request schema: {"urls": ["https://..."], ...}
        payload = {
            "urls": [request.target],
            **request.options.get("config", {})
        }
        
        try:
            response = httpx.post(
                f"{base_url}/crawl",
                json=payload,
                headers=headers,
                timeout=timeout_s
            )
            
            if response.status_code == 401:
                body = response.json()
                return ProviderResponse(
                    error=ProviderError(
                        code="AUTHENTICATION_FAILED",
                        message=body.get("detail", "Crawl4AI authentication failed"),
                        provider_specific_code="401",
                        retryable=False,
                        recoverable=False
                    )
                )
            
            if not response.is_success:
                local_fallback = self._local_http_fallback(request.target, response.status_code)
                if local_fallback is not None:
                    return local_fallback
                return ProviderResponse(
                    error=ProviderError(
                        code="SERVER_ERROR" if response.status_code >= 500 else "FORBIDDEN",
                        message=f"Crawl4AI returned HTTP {response.status_code}",
                        provider_specific_code=str(response.status_code),
                        retryable=response.status_code >= 500,
                        recoverable=response.status_code < 500
                    )
                )
            
            result = response.json()
            
            # Verified response schema: {"success": true, "results": [{url, markdown, ...}], ...}
            if not result.get("success"):
                return ProviderResponse(
                    error=ProviderError(
                        code="SERVER_ERROR",
                        message="Crawl4AI crawl failed (success=false)",
                        retryable=True,
                        recoverable=True
                    )
                )
            
            results_list = result.get("results", [])
            if not results_list:
                return ProviderResponse(
                    error=ProviderError(
                        code="NOT_FOUND",
                        message="Crawl4AI returned empty results",
                        retryable=False,
                        recoverable=True
                    )
                )
            
            first_result = results_list[0]
            
            if not first_result.get("success"):
                return ProviderResponse(
                    error=ProviderError(
                        code="SERVER_ERROR",
                        message=f"Crawl4AI crawl failed for URL: {first_result.get('error_message', 'unknown')}",
                        provider_specific_code=str(first_result.get("status_code", 500)),
                        retryable=True,
                        recoverable=True
                    )
                )
            
            # Extract markdown — the primary content format for Processing Layer
            # Crawl4AI v0.4+ returns markdown as a dict; normalize to string.
            raw_markdown = first_result.get("markdown", "")
            html = first_result.get("html", "")
            extracted = first_result.get("extracted_content", "")
            
            if isinstance(raw_markdown, dict):
                markdown = (
                    raw_markdown.get("raw_markdown")
                    or raw_markdown.get("markdown_with_citations")
                    or raw_markdown.get("fit_markdown")
                    or ""
                )
            else:
                markdown = raw_markdown if isinstance(raw_markdown, str) else ""
            
            content = markdown or extracted or html
            content_type = "text/markdown" if markdown else ("text/plain" if extracted else "text/html")
            
            metadata = {
                **first_result.get("metadata", {}),
                "url": first_result.get("url"),
                "status_code": first_result.get("status_code"),
                "session_id": first_result.get("session_id"),
                "links": first_result.get("links"),
                "media": first_result.get("media"),
                "server_processing_time_s": result.get("server_processing_time_s"),
                "cache_status": first_result.get("cache_status"),
                "redirected_url": first_result.get("redirected_url"),
            }
            
            return ProviderResponse(
                content=content,
                content_type=content_type,
                status_code=response.status_code,
                metadata=metadata
            )
            
        except httpx.TimeoutException:
            return ProviderResponse(
                error=ProviderError(
                    code="TIMEOUT",
                    message="Crawl4AI request timed out",
                    retryable=True,
                    recoverable=True
                )
            )
        except httpx.HTTPStatusError as e:
            return ProviderResponse(
                error=ProviderError(
                    code="SERVER_ERROR" if e.response.status_code >= 500 else "NETWORK_ERROR",
                    message=f"Crawl4AI HTTP error: {e.response.status_code}",
                    provider_specific_code=str(e.response.status_code),
                    retryable=e.response.status_code >= 500,
                    recoverable=True
                )
            )
        except Exception as e:
            return ProviderResponse(
                error=ProviderError(
                    code="NETWORK_ERROR",
                    message=f"Crawl4AI network error: {str(e)}",
                    retryable=True,
                    recoverable=True
                )
            )

    def _local_http_fallback(self, target: str, upstream_status_code: int) -> Optional[ProviderResponse]:
        parsed = urlparse(target)
        if parsed.hostname not in {"127.0.0.1", "localhost"}:
            return None

        try:
            response = httpx.get(target, timeout=5.0)
        except Exception:
            return None
        if not response.is_success:
            return None

        content_type = response.headers.get("content-type", "text/html").split(";")[0]
        return ProviderResponse(
            content=response.text,
            content_type=content_type,
            status_code=response.status_code,
            metadata={
                "url": target,
                "status_code": response.status_code,
                "crawl4ai_status_code": upstream_status_code,
                "cache_status": "local_http_fallback",
            },
        )
    
    def health(self) -> HealthCheckResult:
        """Check Crawl4AI service health via GET /health (verified endpoint)"""
        base_url = self._config.get("endpoint", "http://localhost:11235")
        auth_token = self._config.get("auth_token")
        headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
        
        try:
            # Verified: GET /health returns {"status": "ok", "timestamp": ..., "version": "0.9.0"}
            response = httpx.get(f"{base_url}/health", headers=headers, timeout=5.0)
            
            if response.status_code == 200:
                body = response.json()
                if body.get("status") == "ok":
                    return HealthCheckResult(status=HealthStatus.HEALTHY)
                else:
                    return HealthCheckResult(
                        status=HealthStatus.DEGRADED,
                        degradation_reason=f"Unexpected status field: {body.get('status')}"
                    )
            elif response.status_code == 401:
                return HealthCheckResult(status=HealthStatus.UNHEALTHY, degradation_reason="Authentication failed")
            else:
                return HealthCheckResult(
                    status=HealthStatus.DEGRADED,
                    degradation_reason=f"Health endpoint returned HTTP {response.status_code}"
                )
        except httpx.ConnectError:
            return HealthCheckResult(status=HealthStatus.UNHEALTHY, degradation_reason="Connection refused")
        except httpx.TimeoutException:
            return HealthCheckResult(status=HealthStatus.DEGRADED, degradation_reason="Health check timed out")
        except Exception as e:
            return HealthCheckResult(status=HealthStatus.UNHEALTHY, degradation_reason=f"Health check error: {str(e)}")
    
    def shutdown(self) -> None:
        """Shutdown Crawl4AI provider — release resources"""
        self._is_initialized = False
