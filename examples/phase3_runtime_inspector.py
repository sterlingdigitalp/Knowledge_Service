#!/usr/bin/env python3
"""Inspect Phase 3 intelligence collection runtime state."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from knowledge_service.intelligence.inspector import inspect_intelligence_runtime


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect Phase 3 intelligence collection runtime")
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    args = parser.parse_args()

    report = inspect_intelligence_runtime(args.state_dir)
    if args.format == "markdown":
        print(_to_markdown(report))
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["system_summary"]["status"] == "pass" else 1


def _to_markdown(report: Dict[str, Any]) -> str:
    phase = report.get("phase", "3")
    lines = [f"# Phase {phase} Runtime Inspector", "", "## System Summary"]
    for key, value in report["system_summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Profiles"])
    for profile in report["profiles"]:
        lines.append(
            f"- {profile['name']} ({profile['profile_id']}): "
            f"enabled={profile['enabled']}, "
            f"interests={profile.get('interest_count', 'n/a')}, "
            f"watch_list={profile.get('watch_list_size', 'n/a')}, "
            f"required_podcasts={profile.get('required_podcasts', 'n/a')}"
        )
    if "route_registry" in report:
        lines.extend(["", "## Route Registry"])
        for source in report["route_registry"].get("sources", []):
            lines.append(
                f"- {source['canonical_name']} ({source['source_id']}): "
                f"preferred={source['preferred_route']}, certified={source['certification_status']}, "
                f"confidence={source.get('route_confidence', source.get('transcript_confidence', 'n/a'))}"
            )
    if "information_events" in report:
        lines.extend(["", "## Information Events"])
        for key, value in report["information_events"].items():
            if key != "recent":
                lines.append(f"- {key}: {value}")
    lines.extend(["", "## Discovery"])
    for key, value in report["discovery"].items():
        if key != "latest_run":
            lines.append(f"- {key}: {value}")
    if "route_diagnostics" in report:
        lines.extend(["", "## Route Diagnostics"])
        lines.append(f"- warnings: {report['route_diagnostics'].get('warnings')}")
        for route, stats in (report["route_diagnostics"].get("per_route_statistics") or {}).items():
            lines.append(f"- {route}: success_rate={stats.get('success_rate')}, avg_runtime={stats.get('average_runtime_seconds')}")
    lines.extend(["", "## Corpus"])
    for key in ["episodes", "processed_episodes", "duplicate_episodes", "duplicate_detections", "knowledge_objects", "documents", "chunks", "embeddings", "source_graphs"]:
        lines.append(f"- {key}: {report['corpus'].get(key)}")
    if "personal_intelligence" in report:
        phase4 = report["personal_intelligence"]
        lines.extend(["", "## Personal Intelligence"])
        lines.append(f"- status: {phase4.get('status')}")
        lines.append(f"- claims: {phase4.get('claims', {}).get('total')}")
        lines.append(f"- evidence_backed_claims: {phase4.get('claims', {}).get('evidence_backed')}")
        lines.append(f"- relevance_scores: {phase4.get('relevance', {}).get('total')}")
        lines.append(f"- all_profiles_evaluated: {phase4.get('relevance', {}).get('all_profiles_evaluated')}")
        lines.append(f"- cross_source_clusters: {phase4.get('cross_source', {}).get('clusters')}")
        lines.append(f"- brief_items: {phase4.get('brief_generation', {}).get('item_count')}")
        lines.append(f"- deep_dives: {phase4.get('deep_dives', {}).get('total')}")
        lines.append(f"- warnings: {phase4.get('warnings')}")
    if "analyst" in report:
        analyst = report["analyst"]
        lines.extend(["", "## Analyst Pipeline"])
        lines.append(f"- status: {analyst.get('status')}")
        lines.append(f"- claims: {analyst.get('claims', {}).get('total')}")
        lines.append(f"- scored_claims: {sum((analyst.get('importance', {}).get('distribution') or {}).values())}")
        lines.append(f"- brief_items: {analyst.get('briefing', {}).get('latest_total_items')}")
    lines.extend(["", "## Runtime"])
    lines.append(f"- scheduler: {report['runtime']['scheduler'].get('status')}")
    lines.append(f"- jobs: {len(report['runtime']['jobs'])}")
    lines.append(f"- errors: {len(report['runtime']['errors'])}")
    lines.append(f"- warnings: {report['runtime']['warnings']}")
    lines.extend(["", "## Deduplication"])
    for key, value in report["deduplication"].items():
        lines.append(f"- {key}: {value}")
    if "analyst" in report:
        analyst = report["analyst"]
        lines.extend(["", "## Analyst (Phase 4.1)"])
        lines.append(f"- status: {analyst.get('status')}")
        lines.append(f"- claims: {analyst.get('claims', {}).get('total', 0)}")
        synthesis = analyst.get("synthesis", {})
        lines.append(f"- themes: {synthesis.get('themes', 0)}")
        lines.append(f"- intelligence_items: {synthesis.get('intelligence_items', 0)}")
        lines.append(f"- compression_ratio: {synthesis.get('compression_ratio', 0)}")
        lines.append(f"- claims_per_item: {synthesis.get('claims_per_item', 0)}")
        briefing = analyst.get("briefing", {})
        lines.append(f"- brief_items: {briefing.get('latest_total_items', 0)}")
        lines.append(f"- reading_time_seconds: {briefing.get('reading_time_seconds', 0)}")
        lines.append(f"- brief_version: {briefing.get('version')}")
        lines.append(f"- synthesis_latency: {analyst.get('pipeline', {}).get('synthesis_latency_seconds', {})}")
        lines.append(f"- warnings: {analyst.get('warnings', [])}")
    if "production" in report:
        prod = report["production"]
        lines.extend(["", "## Production (Phase 5.1)"])
        lines.append(f"- status: {prod.get('status')}")
        lines.append(f"- brief_items: {prod.get('production', {}).get('latest_items', 0)}")
        lines.append(f"- reading_time_seconds: {prod.get('production', {}).get('reading_time_seconds', 0)}")
        lines.append(f"- quality_score: {prod.get('production', {}).get('quality_score', 0)}")
        lines.append(f"- personalization_events: {prod.get('personalization', {}).get('event_count', 0)}")
        lines.append(f"- scheduler: {prod.get('scheduler', {}).get('config', {})}")
        if "llm" in prod:
            llm = prod["llm"]
            lines.extend(["", "### LLM Provider"])
            lines.append(f"- active_provider: {llm.get('active_provider')}")
            lines.append(f"- provider_status: {llm.get('provider_status')}")
            lines.append(f"- model: {llm.get('model')}")
            lines.append(f"- latency_ms: {llm.get('latency_ms')}")
            lines.append(f"- estimated_cost_usd: {llm.get('estimated_cost_usd')}")
            lines.append(f"- fallback_events: {llm.get('fallback_events')}")
            lines.append(f"- retries: {llm.get('retries')}")
            lines.append(f"- failure_count: {llm.get('failure_count')}")
            token_usage = llm.get("token_usage") or {}
            lines.append(f"- total_tokens: {token_usage.get('total_tokens', 0)}")
        lines.append(f"- warnings: {prod.get('warnings', [])}")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
