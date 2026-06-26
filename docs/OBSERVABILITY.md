# Observability — Metrics, Tracing, and Logging Specification

## Purpose

This document defines the observability architecture for Knowledge_Service. It specifies what metrics are collected, how traces correlate requests across layers, what logs are recorded, and how operational health is measured and reported.

## Scope

This document covers:
- Metrics taxonomy and definitions
- Distributed tracing model
- Logging standards
- Health check endpoints
- Alerting thresholds and policies
- Dashboard requirements
- Data retention for observability data

## Design Rationale

Observability is designed around Principle 12 (Observability by Default). Every operation produces measurable signals. The system must be fully observable without requiring special instrumentation — observability is built into the architecture, not added as an afterthought.

Three pillars of observability are specified:
1. **Metrics**: Quantitative measurements of system behavior (latency, throughput, error rates)
2. **Traces**: End-to-end correlation of individual requests across all layers
3. **Logs**: Structured records of significant events with contextual information

## Metrics Taxonomy

### Category 1: Request Metrics

Measure the API layer's interaction with applications.

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `ks_api_request_duration_seconds` | Histogram | `endpoint`, `method`, `status_code` | Duration of API requests in seconds |
| `ks_api_requests_total` | Counter | `endpoint`, `method`, `status_code` | Total number of API requests |
| `ks_api_active_requests` | Gauge | `endpoint` | Number of currently processing requests |
| `ks_api_rate_limit_remaining` | Gauge | `api_key_id` | Remaining rate limit quota for the hour |

### Category 2: Acquisition Metrics

Measure the acquisition layer's interaction with providers.

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `ks_acquisition_duration_seconds` | Histogram | `provider_name`, `provider_type`, `status` | Duration of provider acquisitions |
| `ks_acquisitions_total` | Counter | `provider_name`, `provider_type`, `status` | Total acquisition attempts by outcome |
| `ks_acquisition_retries_total` | Counter | `provider_name`, `error_code` | Retry attempts per provider and error type |
| `ks_acquisition_cache_hits_total` | Counter | `source_id` | Cache hits for provider responses |
| `ks_acquisition_cache_misses_total` | Counter | `source_id` | Cache misses requiring fresh acquisition |

### Category 3: Processing Metrics

Measure the processing pipeline's performance and quality.

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `ks_processing_duration_seconds` | Histogram | `stage`, `content_type` | Duration per processing stage |
| `ks_processing_objects_total` | Counter | `stage`, `outcome` | Objects produced/consumed per stage |
| `ks_processing_errors_total` | Counter | `stage`, `error_code` | Processing errors by stage |
| `ks_processing_confidence_scores` | Histogram | `source_type` | Distribution of confidence scores for stored objects |

### Category 4: Storage Metrics

Measure the knowledge layer's storage and retrieval performance.

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `ks_storage_write_duration_seconds` | Histogram | `backend`, `object_type` | Duration of storage write operations |
| `ks_storage_read_duration_seconds` | Histogram | `backend`, `query_type` | Duration of storage read operations |
| `ks_storage_objects_total` | Gauge | `type`, `status` | Number of objects by type and lifecycle status |
| `ks_storage_index_size_bytes` | Gauge | `index_type` | Size of indexes (full-text, vector) in bytes |

### Category 5: Cache Metrics

Measure cache effectiveness.

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `ks_cache_hit_ratio` | Gauge | `cache_level`, `cache_type` | Ratio of cache hits to total requests |
| `ks_cache_evictions_total` | Counter | `cache_level`, `reason` | Cache evictions by level and reason |
| `ks_cache_size_bytes` | Gauge | `cache_level` | Current cache size in bytes |

### Category 6: Source Registry Metrics

Measure source quality signals.

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `ks_source_trust_score` | Gauge | `source_id` | Current trust score for each source |
| `ks_source_freshness_score` | Gauge | `source_id` | Current freshness score for each source |
| `ks_source_status` | Gauge | `source_id` | Source health status (1=healthy, 0=unhealthy) |
| `ks_source_success_rate` | Gauge | `source_id` | Rolling success rate per source |

### Category 7: System Health Metrics

Measure overall platform health.

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `ks_uptime_seconds` | Gauge | — | Platform uptime in seconds |
| `ks_memory_usage_bytes` | Gauge | `component` | Memory usage by component |
| `ks_cpu_usage_ratio` | Gauge | `component` | CPU usage ratio by component |
| `ks_disk_usage_bytes` | Gauge | `partition` | Disk usage by partition |
| `ks_goroutines_active` | Gauge | — | Active goroutine/thread count (language-specific) |

## Distributed Tracing

### Trace Model

Every API request generates a trace that flows through all layers. The trace enables end-to-end visibility into how a knowledge request was fulfilled.

### Trace Context Propagation

| Layer | Trace ID Generation | Span Creation |
|-------|-------------------|---------------|
| API Layer | Generates root trace ID on request receipt | Root span: `api.request` |
| Planning Layer | Inherits trace ID from API Layer | Spans: `planning.analyze`, `planning.select_providers`, `planning.build_plan` |
| Acquisition Layer | Inherits trace ID | Spans: `acquisition.execute_step` (one per step), `acquisition.fallback` |
| Processing Layer | Inherits trace ID | Spans: `processing.stage_{name}` (one per stage) |
| Knowledge Layer | Inherits trace ID | Spans: `storage.write`, `storage.read`, `index.upsert` |

### Span Attributes

Every span includes:
- `request_id`: The API request correlation ID
- `plan_id`: The acquisition plan ID (if applicable)
- `provider_name`: The provider involved (if applicable)
- `status`: Outcome of the operation (`success`, `failed`, `partial`, `skipped`)
- `error_code`: Standardized error code if failed

### Trace Sampling

| Condition | Sampling Rate | Rationale |
|-----------|--------------|-----------|
| All requests (default) | 100% for errors, 10% for success | Errors are always traced; successful traces sampled to reduce storage |
| High-priority applications | 100% | Premium clients get full trace coverage |
| Health check requests | 0% | Operational checks don't need tracing overhead |

### Trace Storage and Retention

- Active traces (requests within last hour): Stored in memory for real-time debugging
- Recent traces (last 24 hours): Stored in distributed tracing backend (e.g., Jaeger, Tempo)
- Aggregated trace data: Retained for 30 days in metrics store
- Raw trace data: Retained for 7 days in tracing backend

## Logging Standards

### Log Levels

| Level | Usage | Examples |
|-------|-------|----------|
| `DEBUG` | Detailed diagnostic information | Provider request/response details, pipeline stage entry/exit |
| `INFO` | Significant operational events | Request received, acquisition completed, source registry updated |
| `WARN` | Unexpected but handled conditions | Retry triggered, partial result returned, cache miss rate high |
| `ERROR` | Error conditions requiring attention | Provider failure after retries, processing pipeline error, storage write failure |
| `FATAL` | System cannot continue | Startup failure, critical dependency unavailable, data corruption detected |

### Log Format

All logs are structured (JSON) with consistent fields:

```json
{
  "timestamp": "2026-06-25T14:30:00Z",
  "level": "INFO",
  "component": "acquisition_layer",
  "request_id": "req-abc-123",
  "plan_id": "plan-xyz",
  "message": "Acquisition step completed successfully",
  "provider_name": "crawl4ai-primary",
  "target": "https://example.com/article",
  "duration_ms": 1200,
  "status": "success"
}
```

### Required Log Fields

| Field | Always Present? | Description |
|-------|----------------|-------------|
| `timestamp` | Yes | ISO 8601 UTC timestamp |
| `level` | Yes | Log level |
| `component` | Yes | Layer or component generating the log |
| `request_id` | Yes (for request-scoped logs) | Correlation ID for the API request |
| `message` | Yes | Human-readable description |

### Contextual Fields (when applicable)

- `plan_id`: Acquisition plan identifier
- `provider_name`: Provider involved in the operation
- `source_id`: Source registry entry identifier
- `object_id`: Knowledge object identifier
- `error_code`: Standardized error code
- `duration_ms`: Operation duration

### Log Redaction

The following must be redacted from all logs:
- API keys and provider credentials
- Full request/response bodies containing PII (hash or truncate)
- Connection strings with embedded credentials

### Log Output

Logs are written to stdout in structured JSON format. Log aggregation is handled by the deployment infrastructure (e.g., Fluentd, Logstash, cloud logging services). No file-based log rotation is implemented within Knowledge_Service.

## Health Checks

### Readiness Probe

**Endpoint**: `GET /api/v1/health`

Returns system health status for load balancers and orchestration platforms.

```json
{
  "status": "healthy",
  "timestamp": "2026-06-25T14:30:00Z",
  "version": "1.0.0",
  "components": {
    "api_layer": {"status": "healthy"},
    "planning_layer": {"status": "healthy"},
    "acquisition_layer": {"status": "healthy"},
    "processing_layer": {"status": "healthy"},
    "knowledge_layer": {"status": "healthy"},
    "providers": {
      "crawl4ai-primary": {"status": "healthy", "last_check": "2026-06-25T14:29:58Z"},
      "searxng-main": {"status": "degraded", "last_check": "2026-06-25T14:29:58Z", "detail": "high_latency"}
    }
  },
  "metrics": {
    "uptime_seconds": 86400,
    "requests_per_minute": 150,
    "cache_hit_ratio": 0.72
  }
}
```

### Liveness Probe

**Endpoint**: `GET /api/v1/health/live`

Simple check that the process is alive and responsive. Returns HTTP 200 if the process can respond to requests.

### Startup Probe

**Endpoint**: Internal only (not exposed externally)

Used during startup to determine when all components are initialized and ready to accept traffic.

## Alerting Policies

### Critical Alerts (Immediate Notification)

| Condition | Threshold | Duration | Action |
|-----------|-----------|----------|--------|
| API error rate | > 5% of requests return 5xx | 5 minutes | Page on-call engineer |
| Provider circuit breaker open | Any provider circuit in Open state | 10 minutes | Page on-call engineer |
| Storage write failures | > 10 writes fail per minute | 2 minutes | Page on-call engineer |
| Platform uptime | Uptime drops below threshold | Immediate | Page on-call engineer |

### Warning Alerts (Next Business Day)

| Condition | Threshold | Duration | Action |
|-----------|-----------|----------|--------|
| Cache hit ratio | < 30% for 1 hour | 1 hour | Investigate cache configuration |
| Average acquisition latency | > 5 seconds p95 | 30 minutes | Review provider performance |
| Source unhealthy count | > 20% of sources unhealthy | 1 hour | Review source registry health |
| Processing pipeline errors | > 5% of objects fail processing | 30 minutes | Review processing configuration |

### Informational Alerts (Weekly Report)

| Condition | Threshold | Action |
|-----------|-----------|--------|
| Trust score decline | Any source drops > 0.1 in trust | Include in weekly quality report |
| Freshness degradation | Sources not acquired in > 7 days | Review acquisition scheduling |
| Growth metrics | New sources registered, objects stored | Include in capacity planning report |

## Dashboard Requirements

### Operational Dashboard (Real-Time)

- Request rate and error rate over time
- Active provider health status
- Cache hit ratio trend
- Acquisition success/failure breakdown by provider
- Processing pipeline throughput

### Quality Dashboard (Daily/Weekly)

- Source trust score trends
- Confidence score distribution for stored objects
- Duplicate detection statistics
- Topic coverage analysis
- Freshness scores across sources

### Capacity Dashboard (Monthly)

- Storage growth rate
- Index size trends
- Provider latency percentiles over time
- Cache effectiveness over time
- Cost metrics (API calls, compute usage)

## Data Retention for Observability

| Data Type | Hot Storage | Warm Storage | Cold Storage |
|-----------|------------|--------------|--------------|
| Live traces | 1 hour | — | — |
| Recent traces | 24 hours in tracing backend | — | — |
| Raw trace data | — | 7 days in tracing backend | — |
| Metrics (detailed) | 30 days | — | Aggregated only |
| Logs | 30 days in log aggregator | 90 days archived | Deleted or compliance-retained |
| Alert history | Indefinite in alerting system | — | — |

## Assumptions

- OpenTelemetry or equivalent tracing framework is available
- Metrics are exported in Prometheus-compatible format
- Logs are consumed by a centralized log aggregation system
- Alerting integrates with the organization's incident management platform

## Tradeoffs

### 100% vs. Sampled Tracing

**Decision**: 100% trace for errors, 10% sample for success.

**Rationale**: Errors require full visibility for debugging; successful traces are less critical and sampling reduces storage costs significantly (90% reduction). High-priority applications get 100% coverage as a configurable option.

### Structured vs. Plain Text Logs

**Decision**: Structured JSON logs exclusively.

**Rationale**: Structured logs enable automated parsing, filtering, and correlation by log aggregation systems. Plain text logs require regex-based parsing that is fragile and error-prone. The tradeoff is slightly larger log size due to JSON overhead, which is negligible compared to storage costs.

### Real-Time vs. Batch Metrics Export

**Decision**: Real-time metrics export (push or pull model).

**Rationale**: Operational dashboards and alerting require near-real-time data. Batch export would introduce latency that delays incident detection. The computational cost of real-time export is minimal compared to the value of timely operational awareness.

## Future Evolution

Future phases may add:
- Distributed tracing integration with application-layer traces (Hermes, BuilderBoard) for end-to-end request visibility across services
- Custom metrics per application consumer (usage analytics, SLA reporting)
- Anomaly detection on metric streams (automated detection of unusual patterns)
- Synthetic monitoring (periodic test acquisitions to verify provider availability proactively)
- Cost attribution metrics (cost per request, cost per knowledge object acquired)

All additions must integrate with the existing three-pillar observability model.
