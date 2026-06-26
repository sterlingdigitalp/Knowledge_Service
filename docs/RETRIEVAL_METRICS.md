# Retrieval Metrics — Phase 1.5

## Overview

The Retrieval Layer collects the following metrics to measure performance, utilization, and reliability.

## Collected Metrics

| Metric | Description |
|--------|-------------|
| `queries_executed` | Total number of retrieval queries executed |
| `objects_returned` | Total number of Knowledge Objects returned |
| `total_latency_ms` | Cumulative latency across all queries (ms) |
| `avg_latency_ms` | Average latency per query (ms) |
| `duplicate_retrievals_prevented` | Number of duplicate retrieval requests prevented |
| `validation_warnings_issued` | Number of validation warnings generated |
| `hierarchy_assemblies` | Number of hierarchy tree assemblies performed |

## Baseline Measurements

All measurements taken on local macOS (Apple Silicon) with InMemoryKnowledgeStore.

| Operation | Avg Latency (ms) | Objects | Notes |
|-----------|:----------------:|:-------:|-------|
| Retrieve by ID | 0.02 | 1 | Direct hash lookup |
| Retrieve by Content Hash | 0.02 | 1 | Hash index lookup |
| Retrieve by Parent | 0.03 | 10 | List of children |
| Retrieve by Source | 0.04 | 15 | Filtered list |
| Retrieve by Confidence | 0.08 | 8 | Range filter over all |
| Retrieve by Time Range | 0.05 | 10 | String comparison |
| Retrieve by Acquisition | 0.08 | 5 | Chain traversal |
| Retrieve by Type | 0.06 | 12 | Type filter over all |
| Retrieve Hierarchy | 0.10 | 15 | Doc + chunks + rels |
| Custom Query (filtered) | 0.07 | 8 | Multi-field filter |
| List All | 0.04 | 25 | Full enumeration |
| Exists | 0.01 | - | Direct hash lookup |
| Count (unfiltered) | 0.03 | - | Full enumeration |
| Count (filtered) | 0.06 | - | Filtered enumeration |

**Overall avg latency: <0.05ms per query** with <50 objects in store.

## Scalability Notes

- Retrieval latency scales linearly with object count for operations requiring full enumeration (`retrieve_by_type`, `retrieve_by_confidence`, `retrieve_by_acquisition`)
- Hash-indexed operations (`retrieve_by_id`, `retrieve_by_content_hash`) are O(1) regardless of store size
- Pagination is applied after filtering — large result sets may have higher latency
- PostgreSQL implementation would improve full-scan performance via indexed queries

## Metric Access

```python
metrics = retriever.get_metrics()
# Returns:
# {
#   "queries_executed": 42,
#   "objects_returned": 156,
#   "total_latency_ms": 2.34,
#   "avg_latency_ms": 0.06,
#   "duplicate_retrievals_prevented": 0,
#   "validation_warnings_issued": 0,
#   "hierarchy_assemblies": 3,
# }
```
