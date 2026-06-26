# Error Strategy — Error Handling Philosophy and Architecture

## Purpose

This document defines the error handling philosophy and architecture for Knowledge_Service. It specifies how errors are classified, propagated, recovered from, and observed across all layers of the platform.

## Scope

This document covers:
- Error classification taxonomy
- Error propagation rules between layers
- Retry and fallback strategies
- Circuit breaker patterns
- Partial result handling
- Error reporting to applications
- Operational error handling vs. application-level errors

## Design Rationale

The error strategy is designed around Principle 9 (Graceful Degradation). Knowledge_Service must continue operating when individual providers fail, because provider availability varies and is outside the platform's control. The system treats failures as expected, not exceptional.

Errors are classified by their recoverability and impact on the overall operation. This classification determines whether to retry, fallback, reduce confidence, or return an error to the application.

## Error Classification Taxonomy

### By Origin

| Category | Description | Examples |
|----------|-------------|----------|
| **Provider errors** | Failures originating from external systems | Timeouts, rate limits, authentication failures, malformed responses |
| **Platform errors** | Failures within Knowledge_Service itself | Processing pipeline failures, storage write failures, planning errors |
| **Client errors** | Invalid requests from applications | Malformed JSON, missing required fields, unauthorized access |
| **Infrastructure errors** | Environmental failures | Network partition, disk full, memory exhaustion |

### By Recoverability

| Level | Description | Action |
|-------|-------------|--------|
| **R0: Non-recoverable** | Cannot be fixed without external intervention | Return error to application with diagnostic information |
| **R1: Retryable** | May succeed on retry (transient failure) | Retry with backoff; if all retries fail, escalate to R2 |
| **R2: Fallback-able** | Primary approach failed but alternative exists | Execute fallback strategy; if fallback also fails, escalate to R3 |
| **R3: Degradable** | Full result not possible but partial result is acceptable | Return partial results with confidence reduction and warning |
| **R4: Ignorable** | Error does not affect the operation's outcome | Log for observability; continue processing |

### By Impact

| Impact | Description | Affected Scope |
|--------|-------------|---------------|
| **I0: Isolated** | Affects only a single provider call or content piece | One acquisition step |
| **I1: Component** | Affects one layer's ability to complete its task | One layer (e.g., processing fails for one document) |
| **I2: Operation** | Affects the entire operation but partial results exist | One API request's result set |
| **I3: Service** | Affects the platform's ability to serve requests | Multiple operations or all requests of a type |

## Error Propagation Rules

### Rule 1: Normalize at Layer Boundaries

Every layer must normalize errors from layers below it before passing them upward. Provider-specific error formats never escape the Provider Layer. Platform-internal error formats never escape their originating layer without being adapted for the consuming layer's understanding.

**Example**: The Acquisition Layer receives `Crawl4AITimeoutError` from a provider. It normalizes this to the standard `ProviderError{code: TIMEOUT, retryable: true}` before passing it to the Planning Layer.

### Rule 2: Preserve Error Context

Each layer adds its own context to errors without losing information from lower layers. The error context chain is preserved for debugging and observability.

**Example**:
```
Original: Crawl4AI returned HTTP 503 on GET https://example.com
Acquisition Layer adds: request_id=req-abc, provider=crawl4ai-primary, step=step-crawl-docs
Planning Layer adds: plan_id=plan-xyz, intent=research, fallback_level=0
API Layer adds: api_endpoint=/knowledge/acquire, client_id=app-123
```

The final error returned to the application contains all context levels, but formatted in a way that doesn't expose internal implementation details.

### Rule 3: Never Suppress Errors

Errors are never silently swallowed. Every error is either:
1. Handled (retried, fallen back, or degraded) with the outcome recorded
2. Propagated upward with added context
3. Logged for observability even if it reaches an Ignorable level

### Rule 4: Distinguish Client Errors from System Errors

Client errors (invalid requests) are returned immediately without triggering retries or fallbacks. System errors (provider failures, processing issues) trigger the recovery strategies defined in this document.

## Retry Strategy

### When to Retry

Retries are applied only to R1 (retryable) errors:
- Network timeouts
- Rate limit responses (with backoff)
- Server errors (5xx from providers)
- Transient connection failures

Retries are NOT applied to:
- Authentication failures (R0 — indicates credential problem, not transient)
- Not found errors (R0 — resource genuinely doesn't exist)
- Client validation errors (R0 — request is malformed)
- Format errors (R0 — content cannot be processed regardless of retry)

### Retry Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_retries` | 3 | Maximum number of retry attempts per provider call |
| `backoff_base_ms` | 1000 | Initial backoff duration in milliseconds |
| `backoff_multiplier` | 2.0 | Multiplier applied to backoff after each retry (exponential) |
| `backoff_jitter` | true | Add random jitter to prevent thundering herd |
| `max_backoff_ms` | 30000 | Maximum backoff duration cap |

### Backoff Calculation

```
backoff = min(backoff_base × multiplier^attempt + jitter, max_backoff)
```

Where `jitter` is a random value between 0 and `backoff_base × 0.1`.

### Retry Scope

Retries are scoped to individual provider calls, not entire acquisition plans. If one provider fails and retries exhaust, the Planning Layer moves to fallback strategies without retrying other providers in the same plan.

## Fallback Strategy

### Fallback Hierarchy

When primary acquisition fails after retries:

```
Primary Provider → Retry (exhausted) → Fallback Provider 1 → Retry → Fallback Provider 2 → ... → Partial Result or Error
```

### Fallback Selection Criteria

Fallback providers are selected based on:
1. **Capability match**: Must be able to acquire the same content type
2. **Status**: Must be healthy (not degraded or unhealthy per Source Registry)
3. **Priority**: Lower priority number = higher fallback priority
4. **Historical success rate**: Higher success rate preferred among equal-capability providers

### Fallback Configuration

Fallback chains are defined in the acquisition plan during planning:

```yaml
fallback_chain:
  - trigger: primary_failed
    steps:
      - provider: searxng-secondary
        target: same_as_primary
      - provider: rss-fallback
        target: same_source_rss_feed
  - trigger: confidence_below_threshold
    steps:
      - provider: backup-crawler
        target: alternative_url_for_same_content
```

### Fallback Limits

- Maximum fallback depth: Configurable per plan (default: 3 levels)
- Each fallback level increments a counter; exceeding the limit returns partial results or error
- Fallbacks do not retry — they are distinct providers, so retries apply independently to each fallback provider

## Circuit Breaker Pattern

### Purpose

Prevents cascading failures when a provider is consistently unavailable. The circuit breaker stops sending requests to a failing provider until it recovers.

### States

| State | Description | Transition To |
|-------|-------------|---------------|
| **Closed** | Normal operation; requests flow through | Open (after failure threshold) |
| **Open** | Requests blocked; immediate failure returned | Half-Open (after recovery timeout) |
| **Half-Open** | Limited test requests allowed | Closed (if test succeeds) or Open (if test fails) |

### Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `failure_threshold` | 5 | Number of consecutive failures to open circuit |
| `recovery_timeout_seconds` | 30 | Time in open state before transitioning to half-open |
| `half_open_max_requests` | 3 | Number of test requests allowed in half-open state |
| `success_threshold` | 2 | Successes needed in half-open to close circuit |

### Per-Provider Circuits

Each provider instance has its own circuit breaker. One provider's failure does not affect circuits for other providers.

## Partial Result Handling

### When Partial Results Are Returned

Partial results are returned when:
1. Some acquisition steps succeeded but others failed (and no fallbacks available)
2. Processing completed successfully but with warnings (e.g., missing metadata)
3. Confidence score is below the plan's target but above the minimum threshold

### Partial Result Format

```json
{
  "results": [...],                    // Successfully acquired knowledge objects
  "warnings": [
    {
      "code": "PARTIAL_ACQUISITION",
      "message": "Only 2 of 3 planned sources were available.",
      "affected_step_ids": ["step-github"],
      "confidence_impact": -0.15
    }
  ],
  "overall_confidence": 0.72,
  "metadata": {
    "request_id": "req-abc-123",
    "acquisition_status": "partial"
  }
}
```

### Confidence Reduction for Partial Results

| Scenario | Confidence Impact |
|----------|-------------------|
| One of N sources missing (N ≥ 3) | -0.05 per missing source |
| All primary providers failed, fallback used | -0.10 |
| Processing completed with warnings | -0.05 per warning category |
| Cache-only result returned (no fresh acquisition) | -0.20 |

Confidence is never reduced below 0.0. If confidence drops to or below the plan's `confidence_floor`, partial results are not returned; instead, an error indicating insufficient evidence is returned.

## Error Reporting to Applications

### HTTP Status Codes

| Situation | Status Code | Body |
|-----------|------------|------|
| Client validation error | 400 Bad Request | Error details with field-level information |
| Authentication failure | 401 Unauthorized | Generic message (never reveal auth mechanism details) |
| Authorization failure | 403 Forbidden | Scope requirement information |
| Resource not found | 404 Not Found | Resource identifier and available alternatives |
| Provider all-failed | 502 Bad Gateway | Which providers failed, confidence of partial results if any |
| Processing internal error | 500 Internal Server Error | Request ID for support; no stack traces |
| Service temporarily unavailable | 503 Service Unavailable | Estimated recovery time if known |

### Never Expose to Applications

The following must never appear in API responses:
- Provider-specific error messages or codes (beyond the standardized code)
- Internal stack traces or exception names
- Credential information or connection strings
- Source Registry internal data structure details
- Planning Layer internal decision logic

### Always Include

Every error response includes:
- `request_id`: For debugging and support correlation
- `code`: Standardized error code
- `message`: Human-readable description appropriate for the audience
- `timestamp`: When the error occurred

## Operational Error Handling

### Platform Internal Errors

Errors within Knowledge_Service that are not triggered by external requests (e.g., background cache cleanup failure, periodic health check failure) are:
1. Logged with full context and stack trace
2. Reported through observability metrics (error counters, alerting)
3. Attempted to self-heal where possible (restart failed component, clear corrupted cache)
4. Escalated to administrators if self-healing fails

### Startup Errors

If Knowledge_Service cannot start due to configuration or dependency errors:
1. Failed components are reported in startup logs
2. The service enters a degraded mode if possible (e.g., start with available providers only)
3. The service refuses to accept traffic if critical components are unavailable
4. Health endpoint reflects the startup failure state

### Shutdown Errors

During graceful shutdown:
1. In-flight requests are given a grace period to complete
2. Provider connections are closed gracefully
3. Pending writes are flushed where possible
4. Shutdown errors are logged but do not prevent termination

## Assumptions

- Retry and circuit breaker libraries are available in the implementation environment
- Logging infrastructure supports structured logging with context propagation
- Monitoring systems can consume error metrics for alerting
- Applications handle partial results gracefully (they receive confidence scores and warnings)

## Tradeoffs

### Aggressive vs. Conservative Retries

**Decision**: Moderate retry policy (3 retries, exponential backoff with jitter).

**Rationale**: Too few retries waste fallback opportunities; too many retries waste time and overwhelm recovering providers. The default balances responsiveness with provider courtesy. Configuration allows per-provider tuning.

### Partial Results vs. Complete Failure

**Decision**: Return partial results when confidence remains above the minimum threshold.

**Rationale**: Applications can make informed tradeoffs based on confidence scores. Returning nothing forces applications to retry or fail, which is worse UX than returning lower-confidence knowledge with clear warnings. The alternative (always requiring complete results) makes the system brittle — one failed provider causes total failure.

### Circuit Breaker Sensitivity

**Decision**: Moderate sensitivity (5 consecutive failures triggers open circuit).

**Rationale**: Too sensitive and healthy providers get unnecessarily blocked by temporary blips; too insensitive and cascading failures aren't prevented. The threshold is configurable per provider based on historical stability patterns.

## Future Evolution

Future phases may add:
- Machine learning-based failure prediction (predict provider failures before they happen)
- Automatic fallback strategy generation based on historical success patterns
- Cross-provider error correlation (detecting when multiple providers fail due to a common upstream issue)
- User-configurable error handling policies per application or request type

All additions must integrate with the existing classification and propagation framework.
