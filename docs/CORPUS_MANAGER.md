# Corpus Manager

The Corpus Manager maintains the persistent Phase 3 intelligence corpus.

## Stored Files
- `profiles.json`
- `episodes.json`
- `source_graphs.json`
- `knowledge_objects.jsonl`
- `growth_history.json`

## Capabilities
- corpus summary
- episode inventory
- transcript count
- KnowledgeObject count
- chunk count
- embedding count
- per-profile statistics
- per-source statistics
- growth history

## Storage Contract
KnowledgeObjects are persisted as JSONL using their canonical `to_dict()` representation, plus Phase 3 metadata including profile, episode, and podcast identifiers.

## Deduplication Boundary
The Corpus Manager records processed and failed episodes. Duplicate prevention is enforced by `DeduplicationStore`; duplicate detections are reported through discovery runs and inspector summaries.

## Certification Result
Latest certification persisted:
- 4 real transcripts
- 384 KnowledgeObjects
- 380 chunks
- 380 embeddings
