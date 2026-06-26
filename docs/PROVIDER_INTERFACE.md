# Provider Interface — Abstraction Specification

## Purpose

This document defines the Provider Interface — the contract that all provider implementations must satisfy. The interface abstracts external systems (crawlers, search engines, APIs, databases, file processors) behind a uniform API so that higher layers never depend on provider-specific types, behaviors, or error formats.

## Scope

This document specifies:
- The Provider Interface contract
- Provider capability declarations
- Provider lifecycle methods
- Error normalization requirements
- Health check semantics
- Extension mechanisms for new provider types

## Design Rationale

The Provider Interface exists to satisfy Principle 2 (Provider Replaceability). Every external system is accessed through this interface. Adding a new provider requires implementing only this interface — no changes to the Acquisition Layer, Processing Layer, or any higher layer are needed.

The interface is intentionally minimal. It exposes capabilities without prescribing implementation details. This allows providers to evolve their internal behavior independently.

## The Provider Interface

Every provider must implement the following four methods:

### `initialize(config: ProviderConfig) -> Result<InitResult, ProviderError>`

**Purpose**: Initialize the provider with configuration and validate that required resources are available.

**Parameters**:
- `config`: Provider-specific configuration including credentials, endpoints, timeouts, and rate limits

**Returns**:
- Success: `InitResult` containing provider metadata (name, version, supported capabilities)
- Failure: `ProviderError` describing why initialization failed

**Behavior**:
- Validates that required configuration fields are present
- Tests connectivity to the external system when possible
- Loads cached credentials or validates credential sources
- Does NOT perform content acquisition (that is the role of `execute`)

**When called**: Once during provider startup, and again if configuration changes at runtime.

### `execute(request: ProviderRequest) -> Result<ProviderResponse, ProviderError>`

**Purpose**: Perform the core provider operation — acquire content from the external system.

**Parameters**:
- `request`: A standardized request object containing the target URL/identifier, acquisition options, and context

**Returns**:
- Success: `ProviderResponse` containing raw content and provider-specific metadata
- Failure: `ProviderError` describing what went wrong

**Behavior**:
- Communicates with the external system using provider-specific protocols
- Handles provider-specific authentication and rate limiting internally
- Returns raw (unprocessed) content — no normalization occurs here
- Attaches provider-specific response headers/metadata to the response object

**When called**: Once per acquisition plan item by the Acquisition Layer.

### `health() -> Result<HealthStatus, ProviderError>`

**Purpose**: Check whether the provider is operational and capable of serving requests.

**Returns**:
- Success: `HealthStatus` containing availability state, last successful operation time, and any degradation indicators
- Failure: `ProviderError` indicating the health check itself failed (provider may be down)

**Behavior**:
- Performs a lightweight check (e.g., ping, simple request) without acquiring meaningful content
- Reports partial health if the provider is degraded but not fully unavailable
- Does NOT perform full content acquisition (that would be too expensive for health checks)

**When called**: Continuously by the system's health monitoring; before each acquisition attempt to avoid calling unhealthy providers.

### `shutdown() -> Result<(), ProviderError>`

**Purpose**: Gracefully shut down the provider, releasing resources and closing connections.

**Returns**:
- Success: Empty result
- Failure: `ProviderError` describing shutdown issues (non-fatal — system continues)

**Behavior**:
- Closes network connections
- Flushes any pending operations
- Releases cached data if appropriate
- Does NOT delete stored knowledge objects (those are managed by the Knowledge Layer)

**When called**: During system shutdown or when a provider is being replaced.

## Provider Request Object

The `ProviderRequest` standardizes how acquisition requests reach providers:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `target` | String | Yes | The target to acquire from (URL, repository path, query string, file path, etc.). Format is provider-specific but the field itself is always a string. |
| `provider_type` | Enum | Yes | Classification of what this request is for: `crawl`, `search`, `fetch_api`, `read_rss`, `query_database`, `process_file`. |
| `options` | Object | Optional | Provider-specific acquisition options (e.g., depth limit for crawlers, result count for search, filter parameters for APIs). |
| `context` | Object | Optional | Acquisition context from the Planning Layer including request ID, freshness requirements, and priority. |

## Provider Response Object

The `ProviderResponse` standardizes how providers return content:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content` | Bytes/String | Conditional | Raw content from the provider. Format depends on provider_type (HTML for crawl, JSON for API, text for RSS, etc.). Omitted if status is error-only. |
| `content_type` | String | Yes | MIME type or format identifier of the content (e.g., `text/html`, `application/json`, `application/pdf`). |
| `status_code` | Integer | Yes | Provider-specific status code (HTTP status for web providers, custom codes for others). |
| `metadata` | Object | Optional | Provider-specific metadata (response headers, pagination info, rate limit remaining, etc.). |
| `error` | ProviderError | Conditional | Error details if the operation failed. Omitted on success. |

## Provider Error Format

All provider errors are normalized to a common format before escaping the Provider Layer:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `code` | Enum | Yes | Standardized error code (see error codes table below). |
| `message` | String | Yes | Human-readable error description. |
| `provider_specific_code` | String | Conditional | Original provider's error code, preserved for debugging. Omitted if no provider-specific code exists. |
| `retryable` | Boolean | Yes | Whether this error should trigger a retry. |
| `recoverable` | Boolean | Yes | Whether the overall acquisition can proceed with reduced results (vs. complete failure). |

### Standardized Error Codes

| Code | Meaning | Retryable? | Recoverable? |
|------|---------|-----------|-------------|
| `TIMEOUT` | Provider did not respond within timeout | Yes | Yes — try another provider |
| `RATE_LIMITED` | Provider rate limit exceeded | Yes (with backoff) | Yes — wait and retry or use fallback |
| `AUTHENTICATION_FAILED` | Invalid credentials | No | No — requires credential update |
| `NOT_FOUND` | Target resource does not exist | No | Yes — skip this target, try others |
| `FORBIDDEN` | Access denied | No | Yes — try another provider or source |
| `SERVER_ERROR` | Provider returned 5xx error | Yes | Yes — retry or use fallback |
| `NETWORK_ERROR` | Connection failed | Yes | Yes — network errors are transient |
| `INVALID_RESPONSE` | Provider returned malformed data | Conditional | Depends on context |
| `UNSUPPORTED_FORMAT` | Content format not supported by this provider | No | Yes — try a different provider type |
| `SHUTDOWN` | Provider is shutting down | No | N/A |

## Provider Capabilities Declaration

Each provider declares its capabilities during initialization. The Planning Layer uses these declarations to determine which providers can satisfy a given knowledge request.

### Capability Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `can_crawl` | Boolean | Yes | Can this provider fetch and parse web pages? |
| `can_search` | Boolean | Yes | Can this provider search for content by query? |
| `can_fetch_api` | Boolean | Yes | Can this provider make authenticated API calls? |
| `can_read_rss` | Boolean | Yes | Can this provider consume RSS/Atom feeds? |
| `can_process_files` | Boolean | Yes | Can this provider process uploaded files (PDF, etc.)? |
| `can_query_database` | Boolean | Yes | Can this provider query databases? |
| `supported_content_types` | Array of Strings | Yes | MIME types or formats this provider can handle. |
| `max_depth` | Integer | Conditional | Maximum crawl depth if the provider supports crawling. |
| `rate_limit` | Object | Conditional | Provider's rate limit information (requests per minute, burst size). |

### Capability Declaration Example

```
Provider A (Crawl4AI):
  can_crawl: true
  can_search: false
  can_fetch_api: true
  can_read_rss: false
  can_process_files: false
  can_query_database: false
  supported_content_types: ["text/html", "application/xhtml+xml"]
  max_depth: 3

Provider B (SearXNG):
  can_crawl: false
  can_search: true
  can_fetch_api: false
  can_read_rss: false
  can_process_files: false
  can_query_database: false
  supported_content_types: ["text/html", "application/json"]

Provider C (GitHub Provider):
  can_crawl: false
  can_search: true
  can_fetch_api: true
  can_read_rss: false
  can_process_files: false
  can_query_database: false
  supported_content_types: ["text/plain", "text/markdown", "application/json"]
```

## Provider Lifecycle

```
[Config] → initialize() → [Ready] ←→ execute() / health() → [Operational]
                                      ↓
                              shutdown() → [Terminated]
```

### State Transitions

| State | Description | Allowed Operations |
|-------|-------------|-------------------|
| `uninitialized` | Provider created but not configured | `initialize()` only |
| `ready` | Initialized and validated, awaiting requests | `execute()`, `health()`, `shutdown()` |
| `operational` | Actively serving requests | `execute()`, `health()`, `shutdown()` |
| `degraded` | Operating with reduced capability | `health()`, `shutdown()` (execute may partially work) |
| `unhealthy` | Not accepting new requests | `shutdown()` only |
| `terminated` | Gracefully shut down | None |

### Health Check Integration

The system's health monitoring uses the `health()` method to maintain a provider status table:

```
Provider    Status      Last Healthy    Degradation Reason
────────    ──────      ────────────    ──────────────────
Crawl4AI    healthy     2026-06-25T14:30  none
SearXNG     degraded    2026-06-25T14:28  high latency (>2s)
GitHub      healthy     2026-06-25T14:29  none
RSS         unhealthy   2026-06-25T13:00  connection refused
```

The Planning Layer consults this table when building acquisition plans. Unhealthy providers are excluded; degraded providers are used only as fallbacks or with adjusted expectations.

## Provider Configuration

Provider configuration is passed during `initialize()` and contains provider-specific settings. The structure varies by provider type but always includes:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | String | Yes | Unique identifier for this provider instance (e.g., "crawl4ai-primary", "searxng-main"). |
| `enabled` | Boolean | Yes | Whether this provider is active. Disabled providers are skipped during planning. |
| `priority` | Integer | Yes | Provider priority within its type class (lower number = higher priority). Used by Planning Layer for selection ordering. |
| `credentials` | Object | Conditional | Provider-specific credentials. Managed securely; never exposed to higher layers. |
| `endpoints` | Object | Conditional | Provider API endpoints or connection strings. |
| `timeout_ms` | Integer | Yes | Request timeout in milliseconds. |
| `max_retries` | Integer | Yes | Maximum number of retry attempts per request. |
| `retry_backoff_ms` | Integer | Yes | Initial backoff duration between retries (exponential backoff multiplier applies). |
| `rate_limit_rpm` | Integer | Conditional | Requests per minute limit for this provider instance. |

## Error Normalization Requirement

**This is a hard requirement.** Provider-specific errors MUST be normalized to the standard `ProviderError` format before being passed to any layer above the Provider Layer. No provider error code, message format, or exception type may escape the Provider Layer.

### Normalization Process

1. Catch all provider-specific exceptions and error responses
2. Map them to standardized error codes using a provider-specific error mapping table
3. Preserve original provider error details in `provider_specific_code` for debugging
4. Set `retryable` and `recoverable` flags based on error semantics
5. Create a new `ProviderError` with the normalized data

### Error Mapping Table (Per Provider)

Each provider implementation maintains an internal mapping from its native error codes to standardized codes:

```
Crawl4AI Error Mapping:
  "TimeoutError" → TIMEOUT
  "TooManyRequests" → RATE_LIMITED
  "403 Forbidden" → FORBIDDEN
  "500 Internal Server Error" → SERVER_ERROR
  "ConnectionRefused" → NETWORK_ERROR

SearXNG Error Mapping:
  "timeout" → TIMEOUT
  "rate_limited" → RATE_LIMITED
  "no_results" → NOT_FOUND (treated as valid empty result, not error)
```

## Extension Points

### Adding a New Provider Type

To add support for a new kind of external system:

1. Add the new type to the `provider_type` enum in `ProviderRequest`
2. Implement the four interface methods for the new provider
3. Declare capabilities in `initialize()`
4. Register the provider in configuration and Source Registry
5. No changes required to any layer above Provider Layer

### Adding New Capabilities

To add a new capability (e.g., video processing):

1. Add `can_process_video` boolean to Capability declaration
2. Extend `supported_content_types` to include video MIME types
3. Implement the capability within `execute()` using provider-specific logic
4. Higher layers discover the new capability through the capabilities declaration — no interface change required

### Provider-Specific Options

The `options` field in `ProviderRequest` and the `config` object in `initialize()` are intentionally flexible. Providers define their own option schemas within these objects. The interface does not prescribe specific options — it only requires that they be passed through without interpretation by higher layers.

## Assumptions

- All providers can be represented as stateful instances with lifecycle methods
- Provider credentials are injected at initialization time, not embedded in code
- Network errors are always retryable unless explicitly marked otherwise
- Health checks must complete within 5 seconds (configurable)

## Tradeoffs

### Why Four Methods?

The interface uses exactly four methods to minimize implementation burden while covering all necessary operations. More methods would increase complexity; fewer would omit essential functionality.

### Why Raw Content in Response?

Providers return raw content because normalization is the responsibility of the Processing Layer, not the Provider Layer. Mixing normalization into providers would violate Principle 2 (replaceability) — a new provider's output format might differ slightly from the old one, and having normalization inside the provider would couple it to specific output expectations.

### Why Not Async Interface?

The interface methods are synchronous by default because the Acquisition Layer manages concurrency at its own level. Providers may implement async internally, but the interface presents a uniform synchronous contract. This simplifies provider implementation while allowing the Acquisition Layer to parallelize calls across providers.

## Future Evolution

Future phases may add:
- Streaming response support for large content acquisition
- Batch execution for acquiring multiple targets in one call
- Provider-specific metrics collection hooks
- Dynamic capability discovery (providers that can report their capabilities at runtime)
- Provider version negotiation (handling API version changes gracefully)

All additions must maintain the four-method core interface. Extensions are additive, never breaking.
