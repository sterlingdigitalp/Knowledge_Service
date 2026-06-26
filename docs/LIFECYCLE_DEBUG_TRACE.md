# Lifecycle Debug Trace — Foundation 1.0

## Execution Timeline

```
[01:35:12.618] ENTER Imports (46.4ms)
[01:35:12.664] ENTER Provider Registry
[01:35:12.664]   ENTER SearXNG initialization
[01:35:15.712]   LEAVE SearXNG — name=searxng-main, version=unknown
[01:35:16.163]   SearXNG health: healthy
[01:35:16.163]   ENTER Crawl4AI initialization
[01:35:16.184]   LEAVE Crawl4AI — name=crawl4ai-primary, version=0.9.0
[01:35:16.197]   Crawl4AI health: healthy
[01:35:16.197] LEAVE Provider Registry (3532.9ms)

[01:35:16.197] ENTER Planner
[01:35:16.197] LEAVE Planner — plan_id=plan-req-debug, steps=2
  Step: search-1 type=search target="What is Crawl4AI?" options={language=en, max_results=5, engines=bing,yahoo}
  Step: crawl-1 type=crawl target="What is Crawl4AI?"

[01:35:16.197] ENTER AcquisitionExecutor
[01:35:16.197]   ENTER executor.execute(plan)
[01:35:17.082] LEAVE executor.execute — bundle.request_id=req-debug
  provider_executions: 2
    ExecutionRecord:
      step_id=search-1, searxng-main (search): status=success, latency_ms=292
      raw_response keys: ['content', 'content_type', 'status_code', 'metadata']
      raw_response['content'] = None
      raw_response['metadata'] keys: ['query', 'results', 'suggestions', ...]
      
    ExecutionRecord:
      step_id=crawl-1, crawl4ai-primary (crawl): status=success, latency_ms=700
      raw_response keys: ['content', 'content_type', 'status_code', 'metadata']
      raw_response['content'] type=str len=22169

  discovered_urls: 10
  acquired_documents: 10

[01:35:17.082] LEAVE AcquisitionExecutor (884.5ms)

[01:35:17.082] ENTER Processing Pipeline
[01:35:17.882] LEAVE Processing Pipeline — 489 KnowledgeObjects produced
  DOCUMENT KOs: 10
  CHUNK KOs: 479

[01:35:17.882] PROCESSING TIMING (800.0ms)

[01:35:17.882] ENTER Storage
[01:35:17.882] LEAVE Storage — objects_stored=489, duplicates_prevented=0

[01:35:17.882] ENTER Retrieval
[01:35:17.882]   retrieve_by_id → 1 objects
[01:35:17.882]   retrieve_by_content_hash → 1 objects
[01:35:17.882] LEAVE Retrieval (0.0ms)

[01:35:17.882] ENTER Verification
  ✓ Content hash verified
  ✓ Raw content hash verified
  ✓ Confidence preserved (0.792...)
  ✓ Acquisition chain present (11 records)
  ✓ Provider output → Processing input is byte-for-byte identical

[01:35:17.882] LEAVE Verification (0.0ms)

============================================================
TEST COMPLETE — Total elapsed: 4464.0ms
============================================================
```

## Runtime Measurements

| Stage | Duration | Objects Created | Warnings | Errors |
|-------|----------|-----------------|----------|--------|
| Imports | 46.4ms | - | - | - |
| Provider Registry | 3532.9ms | 2 providers | - | - |
| Planner | <1ms | 1 plan, 2 steps | - | - |
| AcquisitionExecutor | 884.5ms | 1 bundle, 10 docs | - | - |
| Processing Pipeline | 800.0ms | 489 KOs (10 doc + 479 chunk) | - | - |
| Storage | <1ms | 489 stored | - | - |
| Retrieval | <1ms | 2 queries | - | - |
| Verification | <1ms | - | - | - |

## Provider Response Details

### Search (SearXNG)
- **Latency:** 292ms
- **Results:** 10 URLs discovered
- **Engines used:** bing, yahoo (specified in planner options)
- **Content type:** application/json

### Crawl (Crawl4AI)
- **Latency:** 700ms (first document)
- **Documents acquired:** 10
- **Largest document:** 289,527 bytes (GitHub repo)
- **Average document size:** ~60KB
- **Content type:** text/markdown

## Last Successful Stage

**Verification** — All checks passed:
- Content hash verified ✓
- Raw content hash verified ✓
- Confidence preserved (> 0.0) ✓
- Acquisition chain present (11 records) ✓
- Provider output → Processing input byte-for-byte identical ✓

## First Failing Stage (Before Fix)

**AcquisitionExecutor — Crawl Step**

When SearXNG returned 0 results (engines suspended), the crawl step fell back to crawling the query string "What is Crawl4AI?" as a URL, which failed with HTTP 400 from Crawl4AI.

## Root Cause

Two bugs were identified and fixed:

1. **AcquisitionExecutor** (`src/knowledge_service/planning/executor.py`, line 57):
   - When `urls_to_crawl` was empty, it fell back to `[step.target]` (the query string)
   - Crawl4AI returned HTTP 400 for invalid URLs
   
2. **Planner** (`src/knowledge_service/planning/planner.py`, line 42):
   - Search step didn't specify which engines to use
   - SearXNG's default engine selection tried all engines, most of which were suspended/rate-limited

## Smallest Repair Required

### Fix 1: executor.py (line 57)
```python
# Before (buggy):
targets = urls_to_crawl if urls_to_crawl else [step.target]

# After (fixed):
targets = urls_to_crawl  # Skip crawl if no URLs discovered
```

### Fix 2: planner.py (line 42)
```python
# Before:
options={"language": "en", "max_results": 5}

# After:
options={"language": "en", "max_results": 5, "engines": "bing,yahoo"}
```

## Confidence: High

Both bugs have been identified, fixed, and verified with passing tests. The lifecycle now executes successfully from Question to Verification.
