# Planning Engine — Planning Layer Architecture

## Purpose

This document defines the architecture of the Planning Layer, which determines how Knowledge_Service acquires requested knowledge. The Planning Engine analyzes requests, selects providers, builds acquisition plans, and orchestrates multi-source acquisition strategies.

## Scope

This document specifies:
- Planning Layer responsibilities and boundaries
- Request analysis and intent classification
- Provider selection strategy
- Acquisition plan structure
- Fallback planning
- Stopping conditions
- Orchestration model
- Integration with Source Registry

## Design Rationale

The Planning Layer exists because knowledge acquisition is not a simple request-response operation. Different requests require different strategies:

- A request for "latest Next.js changes" needs official documentation, release notes, and community sources
- A request for "Q2 2026 earnings data" needs financial APIs, press releases, and analyst reports
- A request for "GitHub issue #12345" needs direct repository access

A single acquisition strategy cannot serve all cases. The Planning Engine determines the optimal strategy for each request based on the request content, source quality data, and system state.

The Planning Layer is designed to evolve from simple rule-based strategies in Phase 1 to increasingly sophisticated approaches (constraint-based optimization, learning-based selection) in future phases.

## Request Analysis

### Intent Classification

When a knowledge request arrives, the Planning Engine first classifies its intent:

| Intent Category | Description | Example Request |
|----------------|-------------|-----------------|
| `fact_lookup` | Retrieve specific factual information | "What is the release date of Next.js 15?" |
| `research` | Comprehensive investigation on a topic | "Research the latest changes in Next.js" |
| `verification` | Verify a claim with evidence | "Verify that Next.js 15 supports React 19" |
| `monitoring` | Track changes to specific sources | "Monitor the Next.js blog for new posts" |
| `comparison` | Compare information across sources | "Compare Next.js 14 vs Next.js 15 features" |

Classification determines the acquisition strategy depth:
- `fact_lookup`: Minimal acquisition (one or two high-trust sources)
- `research`: Deep acquisition (multiple source types, cross-referenced)
- `verification`: Evidence-heavy acquisition (conflicting sources explicitly sought)
- `monitoring`: Scheduled/recurring acquisition pattern
- `comparison`: Multi-source parallel acquisition

### Scope Determination

The Planning Engine determines the scope of each request:

| Parameter | Description | Source |
|-----------|-------------|--------|
| `content_types_needed` | What types of content are relevant (blog posts, API docs, code repos) | Request analysis |
| `time_range` | Relevant time window for the information | Request analysis or defaults |
| `geographic_scope` | Geographic relevance (if applicable) | Request analysis |
| `language_preference` | Preferred language(s) for results | Request options |
| `depth_required` | How deep to go (surface facts vs. comprehensive research) | Intent classification + request options |

## Provider Selection

### Selection Criteria

The Planning Engine selects providers based on:

1. **Capability match**: Can the provider handle the required content type?
2. **Source trust score**: What is this source's historical reliability?
3. **Freshness score**: How recently has this source been updated successfully?
4. **Latency history**: How fast does this provider typically respond?
5. **Availability status**: Is the provider currently healthy?
6. **Topic expertise**: Does this source have documented expertise in relevant topics?
7. **Priority configuration**: What is the configured priority for this provider?

### Selection Algorithm (Phase 1)

In Phase 1, provider selection uses a weighted scoring algorithm:

```
provider_score = (trust × 0.35) + (freshness × 0.25) + (inverse_latency × 0.15) + (topic_relevance × 0.15) + (priority_override × 0.10)
```

Weights are configurable and documented in the Configuration specification.

### Selection Algorithm (Future Phases)

Future phases may replace or augment the scoring algorithm with:
- **Constraint-based optimization**: Select providers that satisfy hard constraints (must-have sources) while optimizing soft constraints (preferred order, cost limits)
- **Learning-based selection**: Use historical acquisition success rates to predict optimal provider combinations
- **Reinforcement learning**: Continuously optimize provider selection based on downstream knowledge quality feedback

## Acquisition Plan Structure

An Acquisition Plan is the output of the Planning Engine. It specifies exactly how knowledge should be acquired:

### Plan Object

| Field | Type | Description |
|-------|------|-------------|
| `plan_id` | UUID | Unique identifier for this acquisition plan |
| `request_id` | String | Correlation ID linking to the original API request |
| `intent` | Enum | Classified intent (from Request Analysis) |
| `steps` | Array of AcquisitionStep | Ordered list of acquisition operations |
| `parallel_groups` | Array of Step Groups | Steps that can execute concurrently |
| `fallback_chain` | Array of FallbackPlan | Alternative strategies if primary steps fail |
| `stopping_conditions` | StoppingCriteria | When acquisition is considered complete |
| `evidence_requirements` | EvidenceRequirements | Minimum evidence standards for the result |
| `freshness_policy` | FreshnessPolicy | How current the acquired knowledge must be |
| `created_at` | Timestamp | When the plan was created |

### Acquisition Step

Each step represents one provider acquisition operation:

| Field | Type | Description |
|-------|------|-------------|
| `step_id` | String | Unique identifier within this plan |
| `provider_name` | String | Which provider to use for this step |
| `target` | String | What to acquire (URL, query, path) |
| `provider_type` | Enum | Type of acquisition operation |
| `options` | Object | Provider-specific options |
| `depends_on` | Array of Step IDs | Steps that must complete before this one starts |
| `parallel_with` | Array of Step IDs | Steps that may run concurrently with this one |

### Parallel Execution Groups

Steps within the same parallel group execute concurrently:

```json
{
  "parallel_groups": [
    {
      "group_id": "group-1",
      "step_ids": ["step-search", "step-rss"],
      "description": "Search and RSS in parallel"
    },
    {
      "group_id": "group-2",
      "step_ids": ["step-crawl-docs", "step-crawl-blog"],
      "description": "Crawl documentation and blog in parallel"
    }
  ]
}
```

### Fallback Chain

If primary acquisition steps fail, the fallback chain provides alternative strategies:

| Field | Type | Description |
|-------|------|-------------|
| `trigger` | Enum | Condition that activates this fallback (e.g., `primary_failed`, `confidence_below_threshold`) |
| `fallback_steps` | Array of AcquisitionStep | Alternative acquisition steps to execute |
| `max_fallbacks` | Integer | Maximum number of fallback levels to attempt |

### Stopping Conditions

Define when acquisition is considered complete:

| Field | Type | Description |
|-------|------|-------------|
| `min_sources` | Integer | Minimum number of distinct sources acquired |
| `min_confidence` | Float | Target confidence threshold for assembled result |
| `max_sources` | Integer | Maximum sources to acquire (cost/latency limit) |
| `time_budget_seconds` | Integer | Maximum time to spend on acquisition |
| `evidence_complete` | Boolean | Whether all required evidence types have been collected |

### Evidence Requirements

Define what evidence must be present for the result to be acceptable:

| Field | Type | Description |
|-------|------|-------------|
| `min_source_count` | Integer | Minimum number of independent sources |
| `required_source_types` | Array of Enum | At least one source of each required type (e.g., must include official documentation) |
| `max_age_hours` | Integer | Maximum age of the oldest required source |
| `confidence_floor` | Float | Minimum acceptable confidence for any returned knowledge object |

### Freshness Policy

Define how current the acquired knowledge must be:

| Field | Type | Description |
|-------|------|-------------|
| `freshness_level` | Enum | `current` (real-time), `recent` (within 24h), `any` (any recency acceptable) |
| `cache_bust_allowed` | Boolean | Whether to bypass cache for this request |
| `staleness_threshold_hours` | Integer | Knowledge older than this is considered stale and should be refreshed |

## Example Acquisition Plans

### Plan 1: Fact Lookup (Simple)

```
Intent: fact_lookup
Steps:
  - step-1: SearXNG search for "Next.js 15 release date"
  - step-2: Crawl4AI crawl top result from step-1

Parallel groups: none (sequential)
Fallback chain:
  - If step-1 fails → RSS feed check for Next.js blog
  - If both fail → GitHub releases API check
Stopping conditions: min_sources=1, max_sources=3, time_budget=60s
Evidence requirements: min_source_count=1, required_source_types=[web_page]
Freshness policy: current, cache_bust_allowed=true
```

### Plan 2: Research (Complex)

```
Intent: research
Steps:
  Group A (parallel):
    - step-search: SearXNG search for "Next.js 15 features"
    - step-rss: RSS feed check for Next.js blog
  Group B (depends on Group A):
    - step-crawl-docs: Crawl4AI crawl nextjs.org/docs
    - step-crawl-blog: Crawl4AI crawl top blog result from search
  Group C (parallel with B, depends on search):
    - step-github: GitHub API check for next.js repository releases

Parallel groups: [Group A], [Group B, Group C]
Fallback chain:
  - If all crawlers fail → rely on cached knowledge + RSS only
Stopping conditions: min_sources=3, min_confidence=0.8, max_sources=10, time_budget=300s
Evidence requirements: min_source_count=2, required_source_types=[web_page, api_response], confidence_floor=0.6
Freshness policy: recent, cache_bust_allowed=true
```

## Orchestration Model

### Execution Flow

```
Plan Created → Execute Parallel Groups Sequentially → Collect Results → Assemble Knowledge
     ↓                                              ↓
  Plan ID assigned                              Per-step execution
                                                  ↓
                                          Track success/failure per step
                                                  ↓
                                          Apply fallbacks if needed
                                                  ↓
                                          Check stopping conditions after each group
```

### Concurrency Model

- Steps within a parallel group execute concurrently
- Parallel groups execute sequentially (Group A completes before Group B starts)
- Maximum concurrent provider calls is configurable to prevent overwhelming providers
- Each provider call respects the provider's rate limits

### State Tracking

The Planning Engine tracks plan state throughout execution:

| State | Description |
|-------|-------------|
| `created` | Plan built, awaiting execution |
| `executing` | Steps are being executed |
| `waiting_for_fallback` | Primary steps failed, evaluating fallbacks |
| `completed` | All steps executed, stopping conditions met |
| `partial` | Some steps succeeded, stopping conditions met with reduced results |
| `failed` | All acquisition attempts exhausted without usable results |
| `timeout` | Time budget exceeded before stopping conditions were met |

State transitions are logged for observability and reproducibility.

## Integration Points

### With API Layer

- Receives knowledge requests from the API Layer
- Returns plan execution status to the API Layer (immediately for sync, asynchronously for long-running plans)
- The API Layer never sees internal plan structure; it only sees request acknowledgment and result delivery

### With Acquisition Layer

- Passes acquisition plans to the Acquisition Layer for execution
- Receives per-step results from the Acquisition Layer
- Determines when to trigger fallbacks based on step outcomes

### With Source Registry

- Queries source trust, freshness, latency, topic expertise, and availability data
- Updates source metrics after each acquisition (success/failure, latency, content quality signals)
- Uses accumulated historical data to inform future provider selection

### With Processing Layer

- Receives raw content from the Acquisition Layer after execution
- Passes processed Knowledge Objects to the Knowledge Layer
- May request additional acquisition if processing reveals gaps in evidence

## Design Decisions and Tradeoffs

### Sequential vs Parallel Group Execution

**Decision**: Groups execute sequentially; steps within groups execute in parallel.

**Rationale**: This balances speed (parallelism where safe) with dependency management (sequential when content from one step informs the next). Pure parallel execution would be faster but cannot handle dependent acquisitions (e.g., search results needed before crawl targets are known).

### Scoring vs Rule-Based Selection

**Decision**: Phase 1 uses weighted scoring; future phases may add rule-based constraints and learning.

**Rationale**: Weighted scoring is simple to implement, configure, and debug. It provides a good baseline that can be enhanced later. Pure rule-based systems become unwieldy with many providers; pure learning systems require significant historical data before becoming effective.

### Plan Ephemeral vs Persistent

**Decision**: Acquisition plans are ephemeral (stored only during execution).

**Rationale**: Plans are execution artifacts, not persistent knowledge. Storing them indefinitely wastes storage and creates maintenance burden. However, plan metadata (plan_id, state, outcome) is logged for observability and reproducibility.

## Extension Points

### Adding New Intent Categories

1. Extend the intent enum
2. Define default acquisition strategies for the new intent
3. Update request analysis to classify into the new category
4. No changes required to plan structure or execution model

### Adding New Provider Selection Heuristics

1. Implement a new selection strategy interface
2. Register the strategy in the planning configuration
3. The Planning Engine selects strategies based on request context
4. No changes required to plan structure or execution model

### Adding Adaptive Planning

Future phases may add:
- Plans that modify themselves mid-execution based on intermediate results
- Plans that learn from past acquisition outcomes
- Plans that optimize for cost (API call limits, token usage) as well as quality

All adaptive features extend the existing plan structure without requiring schema changes.

## Assumptions

- Source Registry data is available and reasonably up-to-date when plans are built
- Provider capabilities declared during initialization accurately reflect actual capabilities
- Network conditions are stable enough that historical latency data remains relevant
- The volume of concurrent requests allows reasonable parallelism without resource exhaustion

## Future Evolution

Phase 0 establishes the planning framework. Future phases will:
1. Implement Phase 1 weighted scoring algorithm
2. Add constraint-based planning for complex multi-source acquisitions
3. Integrate Source Registry feedback loops for adaptive selection
4. Add cost-aware planning (API rate limits, token budgets)
5. Evaluate learning-based planning approaches as historical data accumulates

The plan structure defined in this document is designed to support all these evolutions without requiring schema changes.
