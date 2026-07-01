# Route Benchmarks

Phase 3.2 benchmarks compare all acquisition routes per source using real URLs.

## Routes Compared

1. `official_transcript`
2. `youtube_transcript_api`
3. `apple_podcast_transcript`
4. `yt_dlp_whisper`
5. `transcript_mirror`
6. `published_transcript`

## Metrics Measured

- Acquisition success
- Transcript completeness (length, segments)
- Timestamp quality (segment coverage)
- Speaker attribution quality
- Retrieval quality (transcript confidence)
- Runtime seconds
- Dependency requirements
- Maintenance burden

## Latest Runtime Evidence

Certification run `phase32_intelligence_20260701T011651Z` measured:

| Source | Preferred | Confidence | Success Rate |
|--------|-----------|------------|--------------|
| all_in | published_transcript | 0.97 | 100% |
| dwarkesh | published_transcript | 0.95 | 100% |
| founders | published_transcript | 0.95 | 100% |
| peter_attia | published_transcript | 0.95 | 100% |
| lex_fridman | official_transcript | 0.48* | config-backed |

*lex_fridman not in active discovery URLs; certified from acquisition ladder evidence.

## Regenerate

```bash
PYTHONPATH=src ./.venv/bin/python -c "
from knowledge_service.intelligence.route_benchmark import RouteBenchmarkService, generate_route_benchmarks_markdown
from knowledge_service.providers.transcript_provider import TranscriptProvider
from knowledge_service.intelligence.route_registry import AcquisitionRouteRegistry
from knowledge_service.intelligence.state import FileStateStore
import tempfile
state = FileStateStore(tempfile.mkdtemp())
registry = AcquisitionRouteRegistry(state, config_path='data/source_routes.json')
provider = TranscriptProvider()
provider.initialize({})
svc = RouteBenchmarkService(registry, provider)
reports = svc.benchmark_all({'dwarkesh': 'https://podscripts.co/podcasts/dwarkesh-podcast/grant-sanderson-ai-and-the-future-of-math'})
print(generate_route_benchmarks_markdown(reports))
"
```