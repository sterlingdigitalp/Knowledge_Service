# Intelligence Layer 2.0

Intelligence Layer 2.0 (IL2) is an optional synthesis layer that runs **alongside Runtime 1** in Knowledge_Service. It does not replace acquisition, scoring, or the existing analyst pipeline. IL2 improves what users see: canonical topics, analyst briefs, and editorial quality.

## Problem

Runtime 1 excels at collection, corroboration, evidence, scoring, and freshness. It fails at:

- Semantic clustering and duplicate merging
- Entity and canonical topic resolution
- Executive writing and signal prioritization
- Rejecting sponsor CTAs, speech fragments, and intro filler

Example failures from `frontend/data/latest.json` (2026-07-02):

| Runtime 1 Title | Root Cause |
|-----------------|------------|
| Visit Mercury | Sponsor CTA (`mercury.com`) surfaced as theme label |
| Figure Where | Speech fragment stitched into title |
| Welcome Developments | Podcast intro + `Developments` suffix |
| Enterprise AI Agents | Pattern overmatch on weak agent signal |

## Architecture

```
Runtime 1 Pipeline (unchanged)
  Claims → Themes → IntelligenceItems → Ranking → Brief v3

Intelligence Layer 2.0 (optional, KNOWLEDGE_IL2_ENABLED=1)
  IntelligenceItems
    → SemanticClusterEngine
    → CanonicalTopicResolver
    → EditorialSynthesisEngine
    → EditorialQualityGate
    → Filtered IntelligenceItems → Brief v3
```

## Package Layout

```
src/knowledge_service/intelligence_v2/
  config.py              # Feature flag + thresholds
  semantic_cluster.py    # Duplicate topic merging
  canonical_resolver.py  # Evidence-driven titles
  entity_resolver.py     # Entity normalization
  editorial_synthesis.py # Analyst brief cards
  quality_gate.py        # Reject low-quality output
  pipeline.py            # Orchestrator
  integration.py         # Production hook
  evaluation/
    corpus_builder.py    # Historical corpus
    comparison.py        # Old vs new harness
    scorer.py            # Quality dimensions
```

## Enable IL2

```bash
export KNOWLEDGE_IL2_ENABLED=1
bin/morning-intelligence.sh run
```

Runtime 1 remains the default when the flag is unset.

## Analyst Brief Card Schema

IL2 produces cards with:

- TITLE (canonical)
- Executive Summary
- What Happened
- Why It Matters
- Evidence
- Confidence + explanation
- Contradictions
- What To Watch
- Suggested Action
- Supporting Sources

## Integration Point

`production/enhancement.py` calls `apply_intelligence_layer_v2()` after personalized ranking when enabled. Results are persisted in `ProductionResult.intelligence_v2`.

## Evaluation

```bash
python -m knowledge_service.intelligence_v2.evaluation.corpus_builder  # via API
# Or:
python -c "from pathlib import Path; from knowledge_service.intelligence_v2.evaluation.corpus_builder import EvaluationCorpusBuilder; EvaluationCorpusBuilder(Path('.')).build(Path('data/intelligence_v2/evaluation_corpus'))"
```

Corpus: `data/intelligence_v2/evaluation_corpus/`  
Comparison report: `data/intelligence_v2/comparison_report.json`

## Runtime 3 Roadmap

1. Live LLM editorial pass (Grok) after deterministic IL2
2. Cross-run topic memory and regression detection
3. Persona-conditioned action recommendations
4. FEGOS feedback loop into IL2 quality weights