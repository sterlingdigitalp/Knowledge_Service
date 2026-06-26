# Configuration — Philosophy and Structure Specification

## Purpose

This document defines the configuration philosophy and structure for Knowledge_Service. It specifies which behaviors are configurable versus hardcoded, how configuration is organized, and the principles governing configuration changes at runtime.

## Scope

This document covers:
- Configuration philosophy and principles
- Configuration categories and hierarchy
- Per-category configuration parameters
- Runtime vs. restart-required configuration
- Configuration validation
- Default values and their rationale
- Environment-specific configuration

## Design Rationale

Configuration is designed around Principle 8 (Configuration Over Code). Behavioral decisions belong in configuration, not code. Changing how the system operates should never require a code change or redeployment where technically feasible.

The configuration model distinguishes between:
1. **Structural configuration** (what components exist) — may require restart
2. **Behavioral configuration** (how components operate) — should be hot-reloadable
3. **Runtime state** (dynamic data like metrics, caches) — not configuration; managed by the system

## Configuration Philosophy

### Principles

1. **No hardcoded behavior**: Any parameter that affects system behavior must be configurable
2. **Sensible defaults**: Every configuration key has a documented default value that works for typical deployments
3. **Validation at load time**: Invalid configuration is rejected before the system starts (or reloads)
4. **Environment separation**: Development, staging, and production configurations are separate; no environment-specific values in shared configuration
5. **Secrets externalized**: Sensitive values (credentials, tokens) come from a secret manager, not configuration files

### Configuration Format

Configuration is stored in YAML format for readability and tooling support:

```yaml
# Example structure
knowledge_service:
  api:
    port: 8080
    rate_limit:
      requests_per_minute: 1000
  
  providers:
    crawl4ai-primary:
      enabled: true
      priority: 1
  
  storage:
    primary:
      backend: postgresql
```

YAML was chosen over JSON for human-editability and over TOML for nested structure support. The format is implementation-specific; the configuration *structure* defined in this document is what matters, not the serialization format.

## Configuration Categories

### Category 1: API Configuration

Controls the public API layer's behavior.

| Parameter | Default | Hot-Reloadable | Description |
|-----------|---------|---------------|-------------|
| `api.port` | 8080 | No | HTTP listen port |
| `api.tls.enabled` | true | No | Enable HTTPS |
| `api.tls.cert_path` | — | No | Path to TLS certificate |
| `api.tls.key_path` | — | No | Path to TLS private key |
| `api.request_max_size_bytes` | 1048576 (1MB) | Yes | Maximum request body size |
| `api.response_max_size_bytes` | 10485760 (10MB) | Yes | Maximum response body size |
| `api.default_page_size` | 50 | Yes | Default pagination page size |
| `api.max_page_size` | 200 | Yes | Maximum allowed page size |
| `api.version` | v1 | No | Current API version (changes require restart) |

### Category 2: Authentication Configuration

Controls application authentication behavior.

| Parameter | Default | Hot-Reloadable | Description |
|-----------|---------|---------------|-------------|
| `auth.api_key.enabled` | true | Yes | Enable API key authentication |
| `auth.api_key.rotation_days` | 90 | Yes | Maximum lifetime for API keys |
| `auth.api_key.hash_algorithm` | argon2id | No | Algorithm for hashing stored keys (changes require restart) |

### Category 3: Rate Limiting Configuration

Controls request rate limiting behavior.

| Parameter | Default | Hot-Reloadable | Description |
|-----------|---------|---------------|-------------|
| `rate_limit.default.requests_per_minute` | 60 | Yes | Default rate limit per API key |
| `rate_limit.default.burst_multiplier` | 2.0 | Yes | Burst size multiplier |
| `rate_limit.global.requests_per_second` | 1000 | Yes | Global request rate limit |
| `rate_limit.tiers` | — | Yes | Tier definitions (elevated, internal) with custom limits |

### Category 4: Provider Configuration

Controls provider behavior and selection. This is the largest configuration category because each provider type has unique parameters.

#### General Provider Settings

| Parameter | Default | Hot-Reloadable | Description |
|-----------|---------|---------------|-------------|
| `providers.default.timeout_ms` | 30000 | Yes | Default request timeout for all providers |
| `providers.default.max_retries` | 3 | Yes | Default maximum retry attempts |
| `providers.default.retry_backoff_base_ms` | 1000 | Yes | Default initial backoff duration |
| `providers.default.retry_backoff_multiplier` | 2.0 | Yes | Default exponential backoff multiplier |
| `providers.default.circuit_breaker.failure_threshold` | 5 | Yes | Consecutive failures before circuit opens |
| `providers.default.circuit_breaker.recovery_timeout_seconds` | 30 | Yes | Time in open state before half-open test |

#### Provider Instance Configuration (Example)

```yaml
providers:
  crawl4ai-primary:
    enabled: true
    priority: 1
    timeout_ms: 30000
    max_retries: 3
    endpoint: "http://crawl4ai:8080"
    credentials_ref: "vault:secret/data/providers/crawl4ai"
  
  searxng-main:
    enabled: true
    priority: 2
    timeout_ms: 15000
    max_retries: 2
    endpoint: "http://searxng:8080"
    search_params:
      engines: ["google", "bing"]
      language: "en"
      time_range: "year"
```

### Category 5: Planning Configuration

Controls the Planning Layer's decision-making behavior.

| Parameter | Default | Hot-Reloadable | Description |
|-----------|---------|---------------|-------------|
| `planning.default.min_sources` | 1 | Yes | Minimum number of sources for a result |
| `planning.default.max_sources` | 5 | Yes | Maximum sources to acquire per request |
| `planning.default.time_budget_seconds` | 120 | Yes | Default time budget for acquisition |
| `planning.default.min_confidence` | 0.5 | Yes | Minimum confidence threshold |
| `planning.provider_selection.trust_weight` | 0.35 | Yes | Weight for trust score in provider selection |
| `planning.provider_selection.freshness_weight` | 0.25 | Yes | Weight for freshness score |
| `planning.provider_selection.latency_weight` | 0.15 | Yes | Weight for inverse latency |
| `planning.provider_selection.topic_weight` | 0.15 | Yes | Weight for topic relevance |
| `planning.provider_selection.priority_weight` | 0.10 | Yes | Weight for configured priority |

### Category 6: Processing Pipeline Configuration

Controls the Processing Pipeline's behavior at each stage.

| Parameter | Default | Hot-Reloadable | Description |
|-----------|---------|---------------|-------------|
| `processing.clean.strip_scripts` | true | Yes | Remove script/style tags during cleaning |
| `processing.clean.max_content_length_bytes` | 10485760 (10MB) | Yes | Maximum content size to process |
| `processing.chunk.strategy` | semantic | No | Chunking strategy (changes require restart) |
| `processing.chunk.chunk_size_tokens` | 512 | Yes | Target chunk size in tokens |
| `processing.chunk.overlap_tokens` | 50 | Yes | Token overlap between chunks |
| `processing.chunk.min_chunk_size_tokens` | 50 | Yes | Minimum content size before chunking |
| `processing.enrich.compute_confidence` | true | Yes | Enable confidence score computation |
| `processing.enrich.detect_relationships` | true | Yes | Enable relationship detection |
| `processing.enrich.classify_topics` | true | Yes | Enable topic classification |

### Category 7: Storage Configuration

Controls the Knowledge Layer's storage backend selection and behavior.

| Parameter | Default | Hot-Reloadable | Description |
|-----------|---------|---------------|-------------|
| `storage.primary.backend` | postgresql | No | Primary store backend type (changes require restart) |
| `storage.primary.connection` | — | No | Connection string (from secret manager) |
| `storage.primary.pool_size` | 10 | Yes | Database connection pool size |
| `storage.vector.backend` | qdrant | No | Vector store backend type |
| `storage.vector.connection` | — | No | Vector store connection string |
| `storage.cache.backend` | redis | No | Cache backend type |
| `storage.cache.ttl_seconds` | 3600 | Yes | Default cache TTL |
| `storage.retention.default_policy` | default-long-term | Yes | Default retention policy for new objects |

### Category 8: Observability Configuration

Controls metrics, tracing, and logging behavior.

| Parameter | Default | Hot-Reloadable | Description |
|-----------|---------|---------------|-------------|
| `observability.metrics.export_format` | prometheus | No | Metrics export format |
| `observability.metrics.push_interval_seconds` | 15 | Yes | How often metrics are exported |
| `observability.tracing.sampling_rate` | 0.1 | Yes | Fraction of successful requests to trace (0.0-1.0) |
| `observability.tracing.trace_all_errors` | true | Yes | Always trace error requests regardless of sampling |
| `observability.logs.level` | INFO | Yes | Minimum log level |
| `observability.logs.format` | json | No | Log format (changes require restart) |

### Category 9: Source Registry Configuration

Controls how the Source Registry tracks and evaluates sources.

| Parameter | Default | Hot-Reloadable | Description |
|-----------|---------|---------------|-------------|
| `source_registry.trust_ema_decay` | 0.1 | Yes | Exponential moving average decay for trust score |
| `source_registry.freshness_decay_lambda` | 0.01 | Yes | Freshness score exponential decay constant |
| `source_registry.metrics_retention_days` | 90 | Yes | How long raw acquisition samples are retained |
| `source_registry.min_acquisitions_for_topic` | 5 | Yes | Minimum acquisitions before topic association is significant |

### Category 10: Error Handling Configuration

Controls retry, fallback, and circuit breaker behavior.

| Parameter | Default | Hot-Reloadable | Description |
|-----------|---------|---------------|-------------|
| `error_handling.max_fallback_depth` | 3 | Yes | Maximum number of fallback levels per plan |
| `error_handling.partial_result_min_confidence` | 0.3 | Yes | Minimum confidence to return partial results |
| `error_handling.retry.max_attempts` | 3 | Yes | Global maximum retry attempts (overridden by provider-specific) |

## Configuration Hierarchy

Configuration is loaded from multiple sources in priority order (highest to lowest):

```
1. Environment variables (highest priority)
2. Command-line flags
3. Secret manager values (for sensitive configuration)
4. Deployment-specific YAML file (e.g., config.production.yaml)
5. Shared YAML file (config.default.yaml) — committed to version control
6. Hardcoded defaults (lowest priority, fallback only)
```

This hierarchy allows:
- Shared base configuration in version control (items 5-6)
- Environment-specific overrides without modifying shared files (item 4)
- Runtime-sensitive values from secret manager (item 3)
- Quick overrides for testing or emergency changes via environment variables (item 1)

## Configuration Validation

### Load-Time Validation

When configuration is loaded, the following validations are performed:

| Check | Severity | Action on Failure |
|-------|----------|-------------------|
| Required fields present | Error | Reject configuration; system does not start |
| Field types correct | Error | Reject configuration; system does not start |
| Enum values valid | Error | Reject configuration; system does not start |
| Numeric ranges valid | Error | Reject configuration; system does not start |
| Connection strings parseable | Error | Reject configuration; system does not start |
| Secret references resolvable | Error | Reject configuration; system does not start |
| Deprecated fields used | Warning | Log warning; apply default for new field |

### Runtime Validation

Some validations occur at runtime when configuration takes effect:

| Check | Severity | Action on Failure |
|-------|----------|-------------------|
| Provider endpoint reachable | Warning | Provider marked unhealthy; logged |
| Storage backend connection established | Error | Layer fails to initialize; system starts degraded or not at all |
| Cache backend connection established | Warning | Cache disabled; system operates without cache |

## Default Values and Rationale

### Why These Defaults?

Default values are chosen to work for a typical development or small production deployment:

- **Timeouts**: 30 seconds balances provider responsiveness with tolerance for slow providers
- **Retries**: 3 retries provides resilience against transient failures without excessive latency
- **Page sizes**: 50 default, 200 max balances API usability with performance
- **Trust weights**: Equal-ish weighting (0.35/0.25/0.15/0.15/0.10) reflects that trust is most important but freshness and latency matter significantly

Defaults can and should be adjusted per deployment based on actual provider performance characteristics and application requirements.

## Hot-Reload vs. Restart Requirements

### Hot-Reloadable Configuration (No Restart Required)

Behavioral parameters that affect ongoing operations:
- Rate limits
- Timeouts
- Retry counts
- Processing pipeline parameters
- Cache TTLs
- Planning weights
- Log levels
- Source registry metrics

These are re-read from configuration on each operation or at regular intervals.

### Restart-Required Configuration (Requires Deployment Reload)

Structural parameters that affect system initialization:
- API port and TLS settings
- Backend type selections (PostgreSQL → MongoDB requires restart)
- Authentication algorithm changes
- Chunking strategy changes
- Log format changes
- New provider instances (adding a provider requires restart to initialize it)

Restart requirements are documented per parameter. Adding new providers is the most common operation requiring a restart, but it does not require code changes — only configuration updates.

## Environment-Specific Configuration

### Development

```yaml
# config.development.yaml
api:
  port: 8080
  tls:
    enabled: false

providers:
  default:
    timeout_ms: 10000
    max_retries: 1

observability:
  logs:
    level: DEBUG
  tracing:
    sampling_rate: 1.0  # Trace everything in development
```

### Production

```yaml
# config.production.yaml
api:
  port: 443
  tls:
    enabled: true

providers:
  default:
    timeout_ms: 30000
    max_retries: 3

observability:
  logs:
    level: INFO
  tracing:
    sampling_rate: 0.1
```

Environment-specific files are not committed to version control if they contain environment-specific values (endpoints, credentials). They are generated during deployment from templates or injected by the deployment system.

## Configuration Migration

When configuration parameters change between versions:

1. **Additive changes** (new parameters with defaults): No migration needed
2. **Renamed parameters**: Old name logs deprecation warning and maps to new name for one major version
3. **Removed parameters**: Logged as error; system refuses to start until removed from configuration
4. **Type changes**: Treated as breaking change; requires manual migration

Configuration migration guides are provided in release notes for any breaking configuration changes.

## Assumptions

- YAML parsing libraries are available in the implementation environment
- A secret manager service is available for sensitive configuration values
- Configuration files are stored securely with appropriate file permissions
- Deployment systems support environment-specific configuration injection

## Tradeoffs

### YAML vs. JSON vs. TOML

**Decision**: YAML for human-editable configuration; JSON-compatible structure internally.

**Rationale**: YAML's readability reduces configuration errors during manual editing. The internal representation is a typed data structure, not tied to any serialization format. If the implementation language has better tooling for a different format, that format may be used without affecting the configuration *structure* defined in this document.

### Hot-Reload vs. Restart for All Changes

**Decision**: Behavioral changes are hot-reloadable; structural changes require restart.

**Rationale**: Hot-reloading everything is complex and error-prone (e.g., changing database backend type mid-operation would leave in-flight queries with invalid connections). Separating behavioral from structural changes gives the best balance of flexibility and correctness.

### Single Configuration File vs. Multiple Files

**Decision**: Single configuration file per environment, potentially including references to external secret stores.

**Rationale**: Multiple files increase complexity (which file takes precedence? how are they composed?). A single file per environment is simpler to reason about, with secret manager handling sensitive values separately.

## Future Evolution

Future phases may add:
- Configuration validation schemas (JSON Schema / OpenAPI) for automated validation
- Configuration versioning with automatic migration tools
- Runtime configuration discovery (system reports its current configuration via API)
- A/B testing of configuration parameters (test different planning weights without full deployment)
- Configuration auditing (track who changed what and when)

All additions must maintain the hot-reload vs. restart distinction and validation requirements defined in this document.
