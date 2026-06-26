"""Instrument: capture exact duplicate detection scenario in e2e lifecycle."""
import os, sys, time, json

_SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
sys.path.insert(0, _SRC_PATH)
sys.path.insert(0, os.path.dirname(_SRC_PATH))

from src.knowledge_service.registry.provider_registry import ProviderRegistry
from src.knowledge_service.providers.searxng_search_provider import SearXNGSearchProvider
from src.knowledge_service.providers.crawl4ai_provider import Crawl4AIProvider
from src.knowledge_service.planning.planner import RuleBasedPlanner
from src.knowledge_service.planning.executor import AcquisitionExecutor
from src.knowledge_service.processing.pipeline import Pipeline
from src.knowledge_service.storage.postgres.in_memory_store import InMemoryKnowledgeStore, InMemorySourceStore
from src.knowledge_service.storage.repositories.knowledge_repository import KnowledgeRepository
from src.knowledge_service.storage.repositories.source_repository import SourceRepository
from src.knowledge_service.interfaces.provider import ProviderType
from datetime import datetime, timezone

registry = ProviderRegistry()

s = SearXNGSearchProvider("searxng-main")
s.initialize({"endpoint": "http://localhost:8080", "timeout_ms": 15000})
registry.register(s)
c = Crawl4AIProvider("crawl4ai-primary")
c.initialize({
    "endpoint": "http://localhost:11235",
    "auth_token": os.environ.get("KNOWLEDGE_SERVICE_CRAWL4AI_TOKEN", "SterlingKnowledge2026"),
    "timeout_ms": 60000,
})
registry.register(c)

store = InMemoryKnowledgeStore()
source_store = InMemorySourceStore()
knowledge_repo = KnowledgeRepository(store)
source_repo = SourceRepository(source_store)

question = "What is Crawl4AI?"
request_id = f"req-debug-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
planner = RuleBasedPlanner(registry)
plan = planner.plan(question, request_id)
executor = AcquisitionExecutor(registry, source_repo)
bundle = executor.execute(plan)
print(f"Bundle: {len(bundle.acquired_documents)} docs, {len(bundle.discovered_urls)} urls", flush=True)
for i, d in enumerate(bundle.acquired_documents):
    print(f"  doc[{i}]: url={d.url} size={d.content_size_bytes} type={d.content_type}", flush=True)

pipeline = Pipeline()
print("Calling pipeline.process...", flush=True)
import time as _t
_t0 = _t.time()
kobjects = pipeline.process(bundle)
_t1 = _t.time()
print(f"Pipeline done in {_t1-_t0:.3f}s: {len(kobjects)} kobjects", flush=True)
if kobjects:
    first = kobjects[0]
    print(f"First ko: id={first.id} type={first.type} url={first.source_url}", flush=True)
    print(f"Has content_hash: {bool(first.content_hash)}", flush=True)
    print(f"Has raw_content_hash: {bool(first.raw_content_hash)}", flush=True)

stored_ids = []
seen_hashes = {}
duplicate_events = []

for idx, ko in enumerate(kobjects):
    content_hash = ko.content_hash
    existing_id = seen_hashes.get(content_hash)
    
    before = {
        "index": idx,
        "ko.id": ko.id,
        "ko.content_hash": ko.content_hash,
        "ko.raw_content_hash": ko.raw_content_hash,
        "ko.source_url": ko.source_url,
        "ko.type": ko.type.value,
        "is_chunk": bool(ko.parent_id),
        "parent_id": ko.parent_id,
    }
    
    stored_id = knowledge_repo.store(ko)
    
    after = {
        "stored_id": stored_id,
        "was_duplicate": stored_id != ko.id,
        "existing_id_on_record": existing_id,
    }
    
    if stored_id != ko.id:
        duplicate_events.append({**before, **after})
        # Retrieve the existing object for comparison
        existing_ko = knowledge_repo.get_by_id(stored_id)
        print(f"\n=== DUPLICATE #{len(duplicate_events)} at ko[{idx}] ===", flush=True)
        print(f"  New object:     id={ko.id}  hash={ko.content_hash[:16]}...  url={ko.source_url}", flush=True)
        print(f"  Old object:     id={existing_ko.id}  hash={existing_ko.content_hash[:16]}...  url={existing_ko.source_url}", flush=True)
        print(f"  Hash match:     {ko.content_hash == existing_ko.content_hash}", flush=True)
        print(f"  Raw hash match: {ko.raw_content_hash == existing_ko.raw_content_hash}", flush=True)
        print(f"  Type match:     {ko.type == existing_ko.type}", flush=True)
        print(f"  Chunk?          new={bool(ko.parent_id)}  old={bool(existing_ko.parent_id)}", flush=True)
        print(f"  Markdown same:  {ko.markdown == existing_ko.markdown}", flush=True)
        if ko.markdown and existing_ko.markdown:
            print(f"  MD len:         new={len(ko.markdown)}  old={len(existing_ko.markdown)}", flush=True)
    else:
        seen_hashes[content_hash] = ko.id
    
    stored_ids.append(stored_id)

if duplicate_events:
    print(f"\n=== SUMMARY ===", flush=True)
    print(f"Total kobjects: {len(kobjects)}", flush=True)
    print(f"Duplicate events: {len(duplicate_events)}", flush=True)
    print(f"Metrics: objects_stored={knowledge_repo._store.get_metrics()['objects_stored']}, "
          f"duplicates_prevented={knowledge_repo._store.get_metrics()['duplicates_prevented']}", flush=True)
    
    # Check: are duplicates ONLY from same-content sources (same GitHub page)?
    dup_urls = set()
    for d in duplicate_events:
        dup_urls.add(d["ko.source_url"])
    print(f"Duplicate source URLs: {dup_urls}", flush=True)
    
    # Verify: no duplicates for different-content objects
    non_dup = [d for d in duplicate_events if not any(
        d["ko.source_url"] != u and d["ko.content_hash"] == h
        for u, h in seen_hashes.items()
    )]
else:
    print("No duplicates detected", flush=True)

print("\nDONE", flush=True)
