# Provider Discovery Framework — Phase 1.1C

> Design for a reusable mechanism to discover service capabilities, endpoints, and contracts.

## Motivation

Currently, each provider includes ad-hoc discovery logic:
- **Crawl4AI**: Health endpoint returns version; OpenAPI spec available at `/openapi.json`
- **SearXNG**: HTML meta tag for version; no OpenAPI spec; config at `/config`

A unified provider discovery framework would eliminate duplication and ensure every provider is interrogated consistently.

---

## Design Principles

1. **All discovery must happen against live infrastructure** — never read documentation
2. **Discovery results must be verifiable** — same process must produce same results given same service state
3. **Discovery must be non-destructive** — read-only operations only (GET requests, no mutations)
4. **Discovery must be graceful** — partial results are acceptable; missing info does not block initialization
5. **Discovery results should be cacheable** — once discovered, contracts can be snapshot for offline use

---

## Proposed Interface

```python
class ProviderDiscoveryResult:
    version: Optional[str]
    endpoints: Dict[str, EndpointInfo]  # method -> path -> EndpointInfo
    capabilities: Dict[str, Any]
    auth_required: bool
    auth_type: Optional[str]  # "bearer", "apikey", "none"
    openapi_url: Optional[str]
    error: Optional[str]


class EndpointInfo:
    method: str  # GET, POST, PUT, DELETE
    path: str
    content_type: Optional[str]  # returns this content type
    expected_status: int = 200
    params: Optional[Dict[str, ParamInfo]]  # query params
    body_schema: Optional[Dict[str, Any]]   # JSON body schema
    response_schema: Optional[Dict[str, Any]]  # JSON response schema
    verified: bool = False  # whether we tested it live


class ParamInfo:
    name: str
    type: str  # "string", "integer", "boolean"
    required: bool
    default: Optional[Any]


class ProviderDiscoverer:
    """Discovers provider capabilities by interrogating live infrastructure."""
    
    PROBES: ClassVar[List[Dict]] = [
        # Priority-ordered paths to probe
        {"paths": ["/health", "/api/health", "/status"], "expected_key": "status"},
        {"paths": ["/openapi.json", "/api/openapi.json", "/swagger.json", "/api-docs"]},
        {"paths": ["/config", "/api/config"]},
        {"paths": ["/about", "/api/about"]},
        {"paths": ["/", "/index.html"]},
    ]
    
    def discover(self, base_url: str, auth_token: Optional[str] = None) -> ProviderDiscoveryResult:
        ...
    
    def _probe_paths(self, base_url, auth_token, paths) -> List[Dict]:
        """Try each path with GET request; return successful responses."""
        ...
    
    def _detect_auth(self, base_url) -> bool:
        """Send request without auth; if 401/403, auth is required."""
        ...
    
    def _detect_auth_type(self, base_url, paths) -> Optional[str]:
        """Try different auth styles (bearer, apikey querystring, etc.)."""
        ...
    
    def _extract_version(self, responses: List[Dict]) -> Optional[str]:
        """Try to extract version string from any response."""
        ...
    
    def _parse_openapi(self, spec: Dict) -> List[EndpointInfo]:
        """Extract endpoint info from OpenAPI spec."""
        ...
    
    def cache_result(self, result: ProviderDiscoveryResult, path: str) -> None:
        """Persist discovery result for offline use."""
        ...
    
    def load_cached(self, path: str) -> Optional[ProviderDiscoveryResult]:
        """Load cached discovery result."""
        ...
```

---

## Probe Strategy

The discoverer follows a priority-ordered probe sequence:

### Phase 1: Auth Detection
1. Send GET to base URL without auth headers
2. If 401/403, auth is required
3. If 401 with `WWW-Authenticate: Bearer`, auth type is bearer
4. If 401 with `WWW-Authenticate: ApiKey`, auth type is API key
5. Fallback: probe with common auth patterns to find which works

### Phase 2: OpenAPI Discovery
1. Probe `/openapi.json`, `/api/openapi.json`, `/swagger.json`, `/api-docs`
2. If OpenAPI spec found, extract all endpoint schemas, request bodies, response types
3. Mark endpoints as schema-discovered (not yet verified)

### Phase 3: Path Fuzzing
1. Probe common paths in priority order
2. For each successful response, extract:
   - HTTP status code
   - Content-Type
   - Version info from response body
   - Key fields in JSON response
3. Mark endpoints as probe-discovered (live verified)

### Phase 4: Response Structure Analysis
1. For JSON responses, recursively extract field names and types
2. Identify key structural elements (arrays, nested objects)
3. Determine which fields are always present vs. optional
4. Build response schema from observed samples

### Phase 5: Request Parameter Discovery
1. If OpenAPI spec available, extract from schema
2. If not, probe with/without likely parameters to determine required fields
3. Document observed defaults

---

## Integration with Providers

```python
class BaseProvider(Provider):
    """Base provider with integrated discovery."""
    
    discoverer: ProviderDiscoverer
    discovery_result: Optional[ProviderDiscoveryResult]
    
    def discover(self) -> ProviderDiscoveryResult:
        """Run discovery against live infrastructure."""
        base_url = self._config.get("endpoint", self.DEFAULT_ENDPOINT)
        auth_token = self._config.get("auth_token")
        self.discovery_result = self.discoverer.discover(base_url, auth_token)
        return self.discovery_result
    
    def initialize(self, config: Dict[str, Any]) -> InitResult:
        """Standardized initialize with discovery."""
        self._config = config
        discovery = self.discover()
        self._version = discovery.version
        # Use discovery result to validate config, detect capabilities, etc.
        self._is_initialized = True
        return InitResult(name=self.name, version=self._version, capabilities=self._build_capabilities(discovery))
```

---

## Caching

Discovery results should be cached to avoid repeated probes on every initialization:

```python
# Cache location
~/.knowledge_service/provider_cache/{provider_name}.json

# Cache format
{
    "discovered_at": "2026-06-25T12:00:00Z",
    "ttl_seconds": 3600,
    "base_url": "http://localhost:11235",
    "endpoints": {...},
    "version": "0.9.0",
    "auth_required": True,
    "auth_type": "bearer",
    "openapi_url": "http://localhost:11235/openapi.json"
}
```

---

## Migration Path

| Step | Description | Status |
|------|-------------|--------|
| 1 | Implement `ProviderDiscoveryResult` and `EndpointInfo` data classes | Phase 1.2 |
| 2 | Implement `ProviderDiscoverer` with probe steps 1-5 | Phase 1.2 |
| 3 | Refactor Crawl4AI provider to use `BaseProvider` with discovery | Phase 1.2 |
| 4 | Refactor SearXNG provider to use `BaseProvider` with discovery | Phase 1.2 |
| 5 | Add caching layer for discovery results | Phase 1.2 |
| 6 | Add discovery verification (re-run probe periodically) | Phase 1.3 |

---

## Current Status (Phase 1.1C)

Discovery logic remains embedded in each provider:
- **Crawl4AI**: Version discovery via `GET /health`, auth detection, OpenAPI spec explored manually via curl
- **SearXNG**: Version discovery via HTML meta tag, config explored at `/config`

The discovery framework will be extracted in Phase 1.2.
