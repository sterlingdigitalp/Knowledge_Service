# Route Confidence Engine

Phase 3.2 computes route confidence from **measured runtime behavior**, not configuration hardcoding.

## Computed Fields

Per source (`SourceRouteEntry`):

| Field | Source |
|-------|--------|
| `route_confidence` | Weighted runtime formula |
| `certification_score` | Certification-weighted variant |
| `failure_rate` | failures / attempts on preferred route |
| `average_acquisition_time_seconds` | Measured latency |
| `average_transcript_quality` | Completeness + route base quality |
| `average_retrieval_quality` | Episode-level confidence rolling average |
| `next_recertification_at` | 30 days from last certification |
| `certification_history` | Append-only certification records |
| `recommendations` | Registry evolution output |

## Formula

When runtime attempts exist:

```
route_confidence =
  0.35 × success_rate
+ 0.20 × (1 - failure_rate)
+ 0.20 × completeness (avg_length / min_chars)
+ 0.10 × speed_score
+ 0.15 × retrieval_quality
```

When no attempts exist, confidence starts at 50% of route base quality (not a config constant).

## Integration

- `RouteConfidenceEngine.apply_to_entry()` runs after every route attempt
- `AcquisitionRouteRegistry.refresh_all_confidence()` updates all sources
- Collector uses computed `route_confidence` for provenance