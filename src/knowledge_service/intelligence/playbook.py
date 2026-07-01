"""Generate SOURCE_PLAYBOOK.md — institutional knowledge per monitored source."""

from __future__ import annotations

from typing import Any, Dict, List

from .models import now_iso
from .route_registry import AcquisitionRouteRegistry, SourceRouteEntry


def generate_source_playbook(registry: AcquisitionRouteRegistry) -> str:
    lines = [
        "# Source Playbook",
        "",
        "Permanent institutional knowledge for every monitored acquisition source.",
        "",
        f"Generated: {now_iso()}",
        "",
    ]
    for entry in sorted(registry.entries(), key=lambda e: e.source_id):
        lines.extend(_source_section(entry))
        lines.append("")
    return "\n".join(lines)


def _source_section(entry: SourceRouteEntry) -> List[str]:
    preferred_stats = entry.route_statistics.get(entry.preferred_route, {})
    lines = [
        f"## {entry.canonical_name} (`{entry.source_id}`)",
        "",
        "### Why Monitored",
        entry.monitoring_reason or "Configured intelligence profile source",
        "",
        "### Canonical Source",
        f"- Source ID: `{entry.source_id}`",
        f"- URL patterns: {', '.join(f'`{p}`' for p in entry.url_patterns) or 'n/a'}",
        f"- Aliases: {', '.join(entry.name_aliases) or 'n/a'}",
        "",
        "### Acquisition Strategy",
        f"- **Preferred route:** `{entry.preferred_route}`",
        f"- **Fallback chain:** {', '.join(f'`{r}`' for r in entry.fallbacks) or 'none'}",
        f"- **Parser:** `{entry.parser}`",
        "",
        "### Confidence & Certification",
        f"- Route confidence: {entry.route_confidence if entry.route_confidence is not None else 'not computed'}",
        f"- Certification score: {entry.certification_score if entry.certification_score is not None else 'not computed'}",
        f"- Certification status: {entry.certification.status}",
        f"- Last certification: {entry.certification.certified_at or 'n/a'}",
        f"- Next certification: {entry.next_recertification_at or 'n/a'}",
        "",
        "### Quality Metrics",
        f"- Failure rate: {entry.failure_rate if entry.failure_rate is not None else 'n/a'}",
        f"- Avg acquisition time: {entry.average_acquisition_time_seconds}s" if entry.average_acquisition_time_seconds is not None else "- Avg acquisition time: n/a",
        f"- Avg transcript quality: {entry.average_transcript_quality}",
        f"- Avg retrieval quality: {entry.average_retrieval_quality}",
        f"- Timestamp quality (preferred): from segment metadata",
        f"- Speaker quality (preferred): from segment metadata",
        "",
        "### Runtime Metrics (preferred route)",
        f"- Attempts: {preferred_stats.get('attempts', 0)}",
        f"- Successes: {preferred_stats.get('successes', 0)}",
        f"- Failures: {preferred_stats.get('failures', 0)}",
        f"- Avg transcript length: {preferred_stats.get('avg_transcript_length', 0)} chars",
        "",
        "### Known Quirks",
    ]
    if entry.quirks:
        for quirk in entry.quirks:
            lines.append(f"- {quirk}")
    else:
        lines.append("- None documented")
    lines.extend(["", "### Certification History"])
    history = entry.certification_history or []
    if history:
        for record in history[-5:]:
            lines.append(f"- {record.get('certified_at') or record.get('benchmarked_at') or record.get('recorded_at')}: {record.get('event', 'certification')}")
    else:
        for ev in entry.certification.evidence or entry.reason:
            lines.append(f"- {ev}")
    if entry.recommendations:
        lines.extend(["", "### Active Recommendations"])
        for rec in entry.recommendations[-3:]:
            lines.append(f"- [{rec.get('type')}] {rec.get('reason')}")
    return lines