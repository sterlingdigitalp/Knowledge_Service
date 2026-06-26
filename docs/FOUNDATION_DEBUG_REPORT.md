# Foundation Debug Report — Phase 1.6C

## Mission Status: COMPLETE ✅

All integration tests pass. The end-to-end lifecycle executes successfully from Question to Verification.

---

## 1. Execution Timeline

See `docs/END_TO_END_TIMELINE.md` for the complete timeline with timestamps.

**Summary:**
- Total lifecycle execution: ~5 seconds (including provider health checks)
- All 7 stages execute without hanging or errors
- No timeouts, no deadlocks, no infinite loops

---

## 2. Runtime Measurements

| Stage | Duration | Objects Created | Warnings | Errors |
|-------|----------|-----------------|----------|--------|
| Imports | 46ms | - | - | - |
| Provider Registry | 3533ms | 2 providers (SearXNG, Crawl4AI) | - | - |
| Planner | <1ms | 1 plan, 2 steps | - | - |
| AcquisitionExecutor | 885ms | 1 bundle, 10 docs, 10 URLs | - | - |
| Processing Pipeline | 800ms | 489 KOs (10 doc + 479 chunk) | - | - |
| Storage | <1ms | 489 stored objects | - | - |
| Retrieval | <1ms | 2 queries, 2 results | - | - |
| Verification | <1ms | - | - | - |

### Provider Response Details

**Search (SearXNG via Bing/Yahoo engines):**
- Latency: 292ms
- Results: 10 URLs discovered
- Content type: application/json

**Crawl (Crawl4AI):**
- Average latency per document: ~700ms
- Documents acquired: 10
- Largest document: 289,527 bytes (GitHub repo)
- Smallest document: 1,469 bytes (YouTube transcript)
- Content type: text/markdown

---

## 3. Last Successful Stage (Before Fix)

**AcquisitionExecutor — Crawl Step**

The crawl step was failing because when SearXNG returned 0 results, the executor fell back to crawling the query string as a URL:

```python
# Buggy code in executor.py line 57:
targets = urls_to_crawl if urls_to_crawl else [step.target]
# step.target = "What is Crawl4AI?" (a query string, not a URL)
```

Crawl4AI returned HTTP 400 for the invalid URL target.

---

## 4. First Failing Stage (Before Fix)

**Root cause chain:**

1. SearXNG engines suspended/rate-limited → 0 search results
2. `urls_to_crawl` empty → fallback to query string as URL
3. Crawl4AI rejects invalid URL → HTTP 400
4. No documents acquired → 0 KnowledgeObjects
5. Test assertion fails: "At least one document should be acquired"

---

## 5. Root Cause

**Two independent bugs were identified:**

### Bug 1: Invalid URL Fallback in AcquisitionExecutor

**File:** `src/knowledge_service/planning/executor.py`, line 57

When SearXNG returns no results, the executor falls back to crawling the query string as a URL. Crawl4AI rejects this with HTTP 400.

### Bug 2: Unreliable Search Engine Selection in Planner

**File:** `src/knowledge_service/planning/planner.py`, line 42

The search step didn't specify which engines to use, so SearXNG tried all available engines (Brave, Google, DuckDuckGo), most of which were suspended/rate-limited.

---

## 6. Smallest Repair Required

### Fix 1: `src/knowledge_service/planning/executor.py` (line 57)

```python
# Before (buggy):
targets = urls_to_crawl if urls_to_crawl else [step.target]

# After (fixed):
targets = urls_to_crawl  # Skip crawl step when no URLs discovered
```

**Impact:** When search returns no results, the crawl step is gracefully skipped instead of attempting to crawl an invalid URL. This aligns with the plan's `fallback_strategy="skip"` setting.

### Fix 2: `src/knowledge_service/planning/planner.py` (line 42)

```python
# Before:
options={"language": "en", "max_results": 5}

# After:
options={"language": "en", "max_results": 5, "engines": "bing,yahoo"}
```

**Impact:** Search explicitly uses Bing and Yahoo engines (verified working), avoiding suspended/rate-limited engines.

### Fix 3: `integration_tests/test_end_to_end_lifecycle.py` (storage assertion)

The test's storage assertion was updated to correctly handle duplicate detection — when two documents have the same content hash, `store()` returns the existing object's ID (correct behavior). The test now verifies that the returned ID corresponds to an object with matching content_hash.

---

## 7. Confidence: High ✅

**Evidence:**
- All 5 integration tests pass consistently
- Full lifecycle executes without hanging or errors
- Provider output → Processing input is byte-for-byte identical (verified via hash)
- Duplicate detection works correctly
- Graceful failure handling verified for provider failures, malformed HTML, and duplicate acquisitions

---

## Bug Classification

| Bug | Category | Severity | Fix Size |
|-----|----------|----------|----------|
| Invalid URL fallback | Acquisition Layer | High (blocks lifecycle) | 1 line change |
| Engine selection | Planning Layer | Medium (causes empty results) | 1 option added |
| Test assertion | Test Layer | Low (false positive) | Assertion logic update |

---

## Files Modified

### Source Code (2 files, 3 lines changed total)

1. **`src/knowledge_service/planning/executor.py`** — Line 57: Removed fallback to query string
2. **`src/knowledge_service/planning/planner.py`** — Line 42: Added explicit engine selection

### Tests (1 file modified)

3. **`integration_tests/test_end_to_end_lifecycle.py`** — Fixed storage assertion and determinism test logic

### Documentation (3 files created)

4. **`docs/LIFECYCLE_DEBUG_TRACE.md`** — Complete execution trace with timestamps
5. **`docs/END_TO_END_TIMELINE.md`** — Timeline of debugging events
6. **`docs/FOUNDATION_DEBUG_REPORT.md`** — This document

---

## Success Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| One uninterrupted execution path exists | ✅ PASS | Question → Planning → Providers → Bundle → Pipeline → Storage → Retrieval → Verification |
| Real providers feed the real Processing Layer | ✅ PASS | SearXNG + Crawl4AI produce real AcquisitionBundle with raw content |
| No simulated AcquisitionBundle | ✅ PASS | Bundle produced by `AcquisitionExecutor.execute(plan)` |
| Knowledge Objects stored and retrieved successfully | ✅ PASS | 489 KOs stored, retrieval returns correct objects |
| Determinism verified (identical hashes) | ✅ PASS | Same bundle → same content_hash across pipeline runs |
| Hashes verified (raw_content_hash, content_hash) | ✅ PASS | Both hashes computed and preserved through lifecycle |
| Confidence preserved (> 0.0) | ✅ PASS | All KOs have confidence > 0.79 |

---

## Remaining Technical Debt (Out of Scope for Phase 1.6C)

As specified in the mission, the following are explicitly out of scope:

- ❌ Embeddings
- ❌ Semantic search
- ❌ Knowledge graph
- ❌ Research engine
- ❌ Adaptive planning
- ❌ Learning
- ❌ Phase 2 capabilities

### Minor Observations (Not Bugs)

1. **SearXNG engine reliability:** The fix specifies `engines="bing,yahoo"` as a workaround for rate-limited engines. A more robust solution would be to implement engine health checking in the SearXNG provider or add automatic fallback to alternative engines when primary engines are suspended.

2. **Determinism test scope:** The determinism test verifies within-run consistency (same bundle → same KOs) rather than cross-run consistency (different runs with same query). Cross-run consistency is not guaranteed because search results vary over time. This is expected behavior for a web-based system.

3. **Provider initialization latency:** SearXNG health check takes ~3 seconds on first run due to version discovery via HTTP request. This could be optimized by caching the version or skipping it during test runs.

---

## Final Statement

**Execution reaches Stage 7 (Verification) and completes successfully.**

The two bugs identified were:
1. Invalid URL fallback in AcquisitionExecutor when search returns no results
2. Unreliable engine selection causing empty search results

Both have been fixed with minimal changes (3 lines total across 2 source files). The Knowledge Operating System now operates as one coherent system with true end-to-end lifecycle support.
