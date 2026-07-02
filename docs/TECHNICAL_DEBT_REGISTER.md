# Technical Debt Register

> Audit date: 2026-07-02  
> Agent: Knowledge_Service deep technical debt audit  
> Rule applied: only **provably unused** items (zero references) were deleted.

---

## Removed (provably dead)

| Item | Evidence | Action |
|------|----------|--------|
| `_debug_store.py` (repo root) | `rg '_debug_store'` → **0 matches**; `rg 'debug_store'` → **0 matches**; `rg 'Instrument: capture exact duplicate'` → only matched the file itself before deletion. Standalone one-off debug instrument, never imported or referenced in docs/CI. | **DELETED** |

---

## Already absent (no action)

| Item | Evidence |
|------|----------|
| `conftest.py.bak` | `glob '**/conftest.py.bak'` → 0 files; `rg 'conftest.py.bak'` → 0 matches |
| `docs/test.md` | `ls docs/ \| grep '^test'` → no matches; `rg 'docs/test\.md'` → 0 matches |
| `docs/test2.md` | Same as above |

---

## Audited — confirmed in use (not debt)

| Item | Evidence |
|------|----------|
| `src/knowledge_service/intelligence/discoverers/stubs.py` | Imported by 5 discoverer modules: `conference.py`, `interview.py`, `livestream.py`, `earnings.py`, `presentation.py` (`from .stubs import …`). Re-exported via `discoverers/__init__.py` and registered in `DiscovererRegistry.default_discoverers()`. Stub implementations return `[]` by design until venue-specific logic is built. |

---

## Uncertain — document, do not remove

### 1. Duplicate failure-injection test directories

Two directories cover overlapping pipeline failure scenarios:

| Location | Tests | Referenced by |
|----------|-------|---------------|
| `failure_tests/test_failure_injection.py` | **16** pytest cases (`TestFailureInjection`) | `README.md`, `docs/PHASE_1.2B_REPORT.md`, `docs/CURRENT_STATE.md` |
| `tests/failure/test_failure_e2e.py` | **3** pytest cases (`TestFailureInjectionE2E`) | `docs/END_TO_END_CERTIFICATION.md`, `docs/LIFECYCLE_VALIDATION.md`, `docs/P1_6B_FIXES.md` |

**Overlap (same intent, different helpers):**

- Malformed / unclosed HTML
- Empty document
- Large (5 MB) document

**Unique to `failure_tests/` (13 scenarios not in `tests/failure/`):**

- Nested scripts, whitespace-only content, invalid UTF-8, duplicate content in same bundle, missing execution records, corrupted timestamps, missing URL, partial provider failure, mixed content types, extremely nested HTML, special-char-only content, zero-length content, negative content size

**Why uncertain:** Both dirs are collected by pytest and documented. `tests/failure/` is the certification-authority subset; `failure_tests/` is the broader Phase 1.2B suite. Consolidation would change test coverage, not a trivial identical merge.

**Recommendation:** Keep both until a maintainer explicitly merges the 13 unique scenarios into `tests/failure/` and updates certification docs.

---

### 2. `tests/demo.py` — manual demonstration script

| Check | Result |
|-------|--------|
| `rg 'demo\.py'` | 2 matches: self (`Usage:` line) + `docs/PHASE_1.2_REPORT.md` |
| `rg 'tests\.demo'` / `import demo` | 0 matches |
| Pytest collection | Not a test module (no `test_*` functions) |

Standalone Phase 1.2 demo (`AcquisitionBundle` → `Pipeline` → Knowledge Objects). Useful for onboarding but not wired into CI or imports.

**Recommendation:** Keep as documented demo, or move to `examples/` if repo hygiene prefers all runnable scripts outside `tests/`.

---

### 3. Gitignored runtime artifact directories

| Path | Status |
|------|--------|
| `runtime_evidence/` | Listed in `.gitignore`; contains generated certification run outputs |
| `state/` | Listed in `.gitignore`; contains local JSON/JSONL runtime state |

Not source debt — local/generated artifacts. Safe to delete locally; will be recreated by certification scripts.

---

### 4. Low-reference modules (false-positive “unused” candidates)

Automated import scan flagged modules with few direct import sites. Manual review confirms they are wired via registries, `__init__.py` re-exports, or CLI entry points:

| Module | Why kept |
|--------|----------|
| `production.morning.__main__` | CLI entry: `python -m knowledge_service.production.morning` |
| `intelligence.discoverers.{conference,earnings,interview,livestream,presentation}` | Registered in `DiscovererRegistry.default_discoverers()` |
| `intelligence.playbook` | Used by `examples/certify_phase32_runtime.py` + `intelligence/__init__.py` |
| `intelligence.route_benchmark` | Used by `examples/certify_phase32_runtime.py` + `docs/ROUTE_BENCHMARKS.md` |
| `production.llm.parse` | Used by `production/llm/xai_responses.py` |
| `production.embeddings.{neural,sentence_transformer}` | Registered in `production/embeddings/registry.py` |

---

## Parallel stacks — intentionally preserved

Per audit rules, **not** flagged for removal:

- `src/knowledge_service/analyst/` — analyst intelligence stack
- `src/knowledge_service/production/` — production morning-intelligence stack
- `src/knowledge_service/intelligence/` — Phase 3–4 intelligence collection stack

These overlap conceptually (briefing, deep dive, novelty, etc.) but serve different deployment paths and have separate test suites.

---

## Audit commands (reproducible)

```bash
# Zero-reference check for _debug_store (pre-deletion)
rg '_debug_store' .
rg 'debug_store' .

# stubs.py usage
rg 'from \.stubs import' src/knowledge_service/intelligence/discoverers/

# Failure test overlap
.venv/bin/python -m pytest --collect-only failure_tests/
.venv/bin/python -m pytest --collect-only tests/failure/

# demo.py references
rg 'demo\.py' .
```