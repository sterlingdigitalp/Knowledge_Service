# Old vs New Output Comparison

Automated comparison of Runtime 1 brief cards against IL2 output.

## Harness

`intelligence_v2/evaluation/comparison.py`

Report: `data/intelligence_v2/comparison_report.json`

## Aggregate Results (2026-07-02 corpus)

| Metric | Runtime 1 | IL2 |
|--------|-----------|-----|
| Average quality score | 0.551 | 0.735 |
| Average delta | — | +0.184 |
| Improved samples | — | 5/5 |

## Side-by-Side Examples

### Visit Mercury

| | Runtime 1 | IL2 |
|---|-----------|-----|
| Title | Visit Mercury | Mercury Startup Banking Platform |
| Score | 0.544 | 0.708 |
| Accepted | yes (published) | **no** (sponsor CTA) |

IL2 correctly identifies sponsor content and rejects publication.

### Figure Where

| | Runtime 1 | IL2 |
|---|-----------|-----|
| Title | Figure Where | AI Founder Career Positioning |
| Score | 0.562 | 0.740 |
| Failure modes | fm_speech_fragment | (resolved) |

### Welcome Developments

| | Runtime 1 | IL2 |
|---|-----------|-----|
| Title | Welcome Developments | Podcast Intro Segment (Low Signal) |
| Score | 0.506 | 0.727 |
| Accepted | yes | **no** (intro filler) |

### Enterprise AI Agents

| | Runtime 1 | IL2 |
|---|-----------|-----|
| Title | Enterprise AI Agents | Enterprise AI Agent Adoption |
| Score | 0.562 | 0.740 |

### Roman Empire

| | Runtime 1 | IL2 |
|---|-----------|-----|
| Title | Roman Empire | Byzantine Empire Historical Analysis |
| Score | 0.581 | 0.758 |

## Scoring Dimensions

`evaluation/scorer.py` measures:

- title_quality
- summary_quality
- entity_accuracy
- topic_coherence
- signal_usefulness
- actionability
- duplication
- editorial_quality

## Run Comparison

```bash
cd Knowledge_Service
.venv/bin/python3 -c "
from pathlib import Path
import json
from knowledge_service.intelligence_v2.evaluation.comparison import ComparisonHarness

manifest = json.loads(Path('data/intelligence_v2/evaluation_corpus/manifest.json').read_text())
harness = ComparisonHarness()
report = harness.compare_samples(manifest['samples'])
harness.write_report(report, Path('data/intelligence_v2/comparison_report.json'))
print('delta:', report.average_delta)
"
```