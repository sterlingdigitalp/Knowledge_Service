# Source Registry — Source Evaluation and Tracking Specification

## Purpose

This document defines the Source Registry — a dynamic system that evaluates, tracks, and remembers the quality of knowledge sources over time. The registry provides historical data that informs planning decisions, enabling the system to prefer reliable sources and avoid problematic ones.

## Scope

This document specifies:
- Source registration process
- Quality metrics and their computation
- Trust score calculation
- Freshness tracking
- Cache policy management
- Topic expertise assignment
- Historical data retention
- Integration with the Planning Layer

## Design Rationale

The Source Registry exists to implement Principle 6 (Accumulative Learning). Without historical data, every acquisition decision is made in a vacuum. The registry ensures that the system learns from past acquisitions: sources that consistently provide high-quality, fresh content are preferred; sources that frequently fail or provide stale content are deprioritized.

The registry is dynamic — it updates continuously as new acquisition results arrive. It is not a static configuration file; it is a living data structure that reflects the system's accumulated experience.

## Source Registration

### Registration Methods

Sources enter the registry through three paths:

| Path | Description | Initial State |
|------|-------------|---------------|
| **Explicit registration** | Administrator manually registers a source with known properties | Configured trust, topics, and cache policy; freshness starts neutral |
| **Automatic discovery** | Source URL is encountered during acquisition (e.g., linked from another source) | All metrics start at default values; requires validation before use |
| **Provider declaration** | Provider declares it can serve a particular source pattern during initialization | Metrics start at defaults; treated as provider-managed source |

### Registration Data

When a source is registered, the following data is captured:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | String | Yes | Unique source identifier. Format: `{provider_type}-{slug}` (e.g., `web-nextjs-blog`). Must be globally unique. |
| `name` | String | Yes | Human-readable name (e.g., "Next.js Official Blog") |
| `url` | URI | Conditional | Primary URL of the source. Required for web-based sources. |
| `type` | Enum | Yes | Source type classification: `web_page`, `api`, `rss_feed`, `github_repo`, `pdf_collection`, `database`, `other`. |
| `owner` | String | Optional | Owning organization or individual (e.g., "Vercel", "Mozilla Foundation") |
| `topics` | Array of Strings | Optional | Initial topic expertise assignment. Populated over time by the registry itself. |
| `cache_policy` | Object | Yes | Default cache policy for this source (see Cache Policy section). |
| `registration_method` | Enum | Yes | How the source entered the registry: `manual`, `discovered`, `provider_declared`. |
| `registered_at` | Timestamp | Yes | When the source was first registered. |

## Quality Metrics

The Source Registry tracks multiple quality metrics for each source. These metrics are computed from acquisition outcomes and historical data.

### Trust Score

**Definition**: A measure of how reliable and accurate content from this source has been, based on historical evidence.

**Range**: 0.0 (untrustworthy) to 1.0 (highly trustworthy)

**Computation**:
```
trust_score = weighted_average(historical_quality_signals)
```

Quality signals include:
- **Source authority**: Is the source an official/authoritative publisher? (static, set at registration)
- **Content accuracy**: Have downstream verifications confirmed content accuracy? (dynamic, accumulated over time)
- **Consistency**: Does the source provide consistent information across acquisitions? (dynamic)
- **Error rate**: How often does this source return errors or malformed content? (dynamic)

**Update frequency**: Updated after each acquisition attempt. Uses exponential moving average with decay factor of 0.1 (new results influence score but don't cause dramatic swings).

### Freshness Score

**Definition**: A measure of how recently and regularly this source publishes new content.

**Range**: 0.0 (stale, never updated) to 1.0 (very recent, frequently updated)

**Computation**:
```
freshness_score = f(time_since_last_acquisition, acquisition_frequency, publication_pattern)
```

Factors:
- **Recency**: Time elapsed since last successful acquisition (shorter = higher score)
- **Frequency**: How often the source publishes new content (more frequent = higher score)
- **Predictability**: How regular the publication pattern is (regular = higher confidence in freshness)

**Decay model**: Freshness score decays exponentially based on time since last acquisition:
```
freshness(t) = initial_freshness × e^(-λt)
```
Where λ is a decay constant configurable per source type.

**Reset behavior**: Successful acquisition of new content resets freshness toward 1.0. Stale acquisitions (no new content found) accelerate decay.

### Latency History

**Definition**: Historical record of acquisition latency for this source.

**Tracked metrics**:
| Metric | Description |
|--------|-------------|
| `avg_latency_ms` | Average response time across all acquisitions |
| `p50_latency_ms` | Median response time |
| `p95_latency_ms` | 95th percentile response time |
| `p99_latency_ms` | 99th percentile response time |
| `latency_trend` | Direction of latency change: improving, stable, degrading |

**Update frequency**: Updated after each acquisition. Sliding window of last 100 acquisitions.

### Success Rate

**Definition**: Percentage of successful acquisition attempts out of total attempts.

**Computation**:
```
success_rate = successful_attempts / total_attempts
```

**Thresholds**:
| Range | Interpretation | Planning Action |
|-------|---------------|-----------------|
| 0.95 - 1.0 | Excellent | Preferred source |
| 0.80 - 0.94 | Good | Normal use |
| 0.60 - 0.79 | Degraded | Use as fallback only |
| < 0.60 | Poor | Exclude from planning until recovery |

**Update frequency**: Updated after each acquisition attempt. Sliding window of last 50 attempts.

### Historical Usefulness

**Definition**: How often content from this source has been retrieved or cited by other knowledge objects.

**Computation**:
```
usefulness_score = f(retrieval_count, citation_count, recency_of_use)
```

Factors:
- **Retrieval count**: Number of times content from this source was returned in response to application queries
- **Citation count**: Number of knowledge objects that cite this source
- **Recency**: How recently the source's content has been used (recent use increases score)

**Purpose**: Identifies sources that are not just reliable but actually valuable to applications. High-usefulness sources may be prioritized even if their trust score is slightly lower than alternatives.

## Topic Expertise

### Assignment Process

Sources develop topic expertise through observation:

1. **Initial assignment**: Set at registration time by the administrator based on known source characteristics
2. **Automatic refinement**: After each acquisition, the processed content's topics are compared against the source's declared topics. Matches reinforce existing assignments; new frequent topics are suggested for addition.
3. **Confidence per topic**: Each topic association has a confidence score (0.0-1.0) reflecting how strongly the source is associated with that topic

### Topic Confidence Computation

```
topic_confidence = acquisition_count_with_topic / total_acquisitions_from_source
```

A source must have at least 5 acquisitions within a topic before that topic association is considered significant (confidence threshold: 0.3 minimum).

### Planning Layer Usage

When the Planning Engine analyzes a request, it queries sources by topic expertise:
- Sources with high topic confidence for relevant topics are ranked higher
- Sources with low or no topic association for requested topics are deprioritized
- Topic expertise is one factor in provider selection (alongside trust, freshness, latency)

## Cache Policy

### Policy Structure

Each source has a cache policy that controls how long acquired content is cached before re-acquisition:

| Field | Type | Description |
|-------|------|-------------|
| `max_age_seconds` | Integer | Maximum time to serve cached content without re-acquisition |
| `stale_while_revalidate` | Integer | Time to continue serving stale cache while fetching fresh content in background |
| `cache_key_strategy` | Enum | How cache keys are generated: `url_exact`, `url_pattern`, `source_id` |
| `invalidate_on_plan` | Boolean | Whether to invalidate cache when a new acquisition plan references this source |

### Policy Defaults by Source Type

| Source Type | Default Max Age | Rationale |
|-------------|----------------|-----------|
| `web_page` (blog) | 3600s (1 hour) | Blogs update frequently |
| `web_page` (documentation) | 86400s (24 hours) | Docs change less often |
| `api` | 300s (5 minutes) | APIs may return real-time data |
| `rss_feed` | 1800s (30 minutes) | Feeds update regularly |
| `github_repo` | 3600s (1 hour) | Repos change with commits |
| `pdf_collection` | 604800s (7 days) | PDFs are relatively static |
| `database` | 60s (1 minute) | Databases may have real-time data |

### Policy Override

Administrators can override default cache policies per source. The Planning Layer respects configured cache policies when deciding whether to use cached content vs. re-acquire.

## Source Status

### Status Values

| Status | Description | Effect on Planning |
|--------|-------------|-------------------|
| `healthy` | Operating normally | Included in provider selection |
| `degraded` | Elevated error rate or latency | Used as fallback; confidence reduced |
| `unhealthy` | Consistent failures | Excluded from planning until recovery |
| `paused` | Temporarily disabled by administrator | Excluded regardless of health metrics |

### Status Transitions

```
healthy ←→ degraded → unhealthy
   ↑           ↓         │
   └──── paused ─────────┘
```

- **healthy → degraded**: Triggered when error rate exceeds threshold or latency spikes persist
- **degraded → unhealthy**: Triggered when success rate drops below 0.60
- **unhealthy → healthy**: After consecutive successful acquisitions (configurable count, default: 3)
- **paused → any**: Administrator-controlled; status determined by health check after unpausing

## Historical Data Retention

### Metrics Retention Periods

| Metric Type | Retained For | Purpose |
|-------------|-------------|---------|
| Trust score (computed) | Indefinite | Long-term source quality assessment |
| Freshness score (computed) | Indefinite | Ongoing freshness tracking |
| Latency samples | 90 days | Recent performance analysis |
| Success/failure records | 365 days | Trend analysis and planning optimization |
| Acquisition audit entries | 90 days active, then archived | Reproducibility and debugging |
| Topic association counts | Indefinite | Long-term expertise tracking |

### Data Aggregation

Raw acquisition samples are aggregated into summary statistics after the retention period:
- Individual latency measurements → rolling averages and percentiles
- Success/failure records → success rate calculations
- Raw content hashes → deduplication references

Aggregated data is retained indefinitely; raw samples have finite retention.

## Integration with Planning Layer

### Query Interface

The Planning Layer queries the Source Registry through a read-only interface:

```
SourceRegistry Interface (read methods):
  - get_source(id) -> SourceEntry
  - search_by_topic(topic, min_confidence) -> List<SourceEntry>
  - get_health_status(source_id) -> Status
  - get_trust_score(source_id) -> Float
  - get_freshness_score(source_id) -> Float
  - list_healthy_sources() -> List<SourceEntry>
```

### Planning Decisions Informed by Registry

| Decision | Registry Data Used |
|----------|-------------------|
| Provider selection | Trust score, topic expertise, status, latency history |
| Acquisition ordering | Freshness score (fresh sources first), priority configuration |
| Fallback planning | Success rate (sources with higher rates are primary; lower-rate sources are fallbacks) |
| Cache decision | Cache policy, freshness score, stale-while-revalidate settings |
| Confidence computation | Source trust score is a component of knowledge object confidence |

### Feedback Loop

After each acquisition completes:
1. Acquisition results (success/failure, latency, content quality signals) are sent to the Source Registry
2. The registry updates metrics for the affected source(s)
3. Updated metrics influence future planning decisions
4. This creates a continuous learning loop: better data → better plans → better acquisitions → better data

## Extension Points

### Adding New Quality Metrics

New metrics can be added by:
1. Defining the metric's computation logic
2. Adding it to the SourceEntry schema
3. Integrating it into the Planning Layer's selection algorithm
4. No changes required to registry storage or update mechanisms

### Adding New Source Types

New source types extend the type enum and may have different default cache policies. The registration process is type-agnostic; only the defaults and processing handlers differ.

### External Trust Signals

Future phases may incorporate external trust signals:
- SSL certificate validity and age
- Domain authority scores from third-party services
- Community reputation data
- Content verification against known facts

These would be integrated as additional inputs to the trust score computation without changing the registry interface.

## Assumptions

- Source identifiers are stable over time (a source's ID doesn't change)
- Topic taxonomies can evolve without breaking existing associations
- Acquisition audit data is available for metric computation
- The Planning Layer reads from the registry synchronously during plan construction

## Tradeoffs

### Computed vs. Configured Metrics

**Decision**: Trust and freshness are primarily computed from historical data, with configuration providing initial values and bounds.

**Rationale**: Computed metrics reflect actual system experience; configured metrics reflect human judgment. Combining both gives the best of both worlds — initial guidance that is refined by experience. Purely configured metrics become stale; purely computed metrics lack initial direction.

### Real-time vs. Batch Updates

**Decision**: Metrics are updated in real-time after each acquisition.

**Rationale**: Planning decisions need current data. Batch updates would introduce staleness into planning. The computational cost of updating a few floating-point values per acquisition is negligible compared to the value of accurate planning data.

### Per-Source vs. Aggregate Tracking

**Decision**: Metrics are tracked per source, not just per provider type.

**Rationale**: Two sources served by the same provider (e.g., two different blogs crawled by Crawl4AI) may have very different quality characteristics. Per-source tracking enables fine-grained planning decisions. The tradeoff is increased storage and computation for many small sources.

## Future Evolution

Future phases may add:
- Automated source discovery and registration workflows
- Cross-reference validation (comparing content from multiple sources to detect inaccuracies)
- Source ownership verification (confirming that a source is genuinely controlled by its claimed owner)
- Community-sourced quality reports (allowing application users to flag unreliable sources)
- Predictive freshness modeling (predicting when a source will next publish based on historical patterns)

All additions must integrate with the existing metric framework without requiring schema restructuring.
