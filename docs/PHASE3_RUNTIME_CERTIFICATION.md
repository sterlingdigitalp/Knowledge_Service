# Phase 3 Runtime Certification

Latest certified artifact directory:

`runtime_evidence/phase3_intelligence_20260701T002459Z`

## Result
PASS

## Certified Chain
New live podcast episode from configured podcast page -> discovered automatically -> deduplicated -> transcript acquired -> KnowledgeObjects created -> corpus updated -> Runtime Inspector updated -> restarted scheduler detects duplicates and performs no duplicate ingestion.

## Real-World Sources
- Dwarkesh Podcast
- All-In Podcast
- Founders
- The Peter Attia Drive

## Profiles
- AI
- Investing
- Founders
- Longevity

## Runtime Counts
- processed episodes: 4
- transcripts: 4
- KnowledgeObjects: 384
- chunks: 380
- embeddings: 380
- source graphs: 12
- source hashes: 4
- acquisition hashes: 4
- transcript hashes: 4
- restart duplicate detections: 4

## Reproduce
```bash
PYTHONPATH=src ./.venv/bin/python examples/certify_phase3_intelligence_collection.py
```

## Remaining Blockers
None in the latest certification artifact.
