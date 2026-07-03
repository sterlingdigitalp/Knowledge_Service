"""Build evaluation corpus from PCC/Hermes/Knowledge_Service historical artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..canonical_resolver import detect_title_failure_modes
from ..models import CorpusSample


@dataclass
class CorpusManifest:
    version: str = "1.0"
    sample_count: int = 0
    sources: List[str] = None  # type: ignore[assignment]
    samples: List[CorpusSample] = None  # type: ignore[assignment]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "sample_count": self.sample_count,
            "sources": list(self.sources or []),
            "samples": [sample.to_dict() for sample in (self.samples or [])],
        }


class EvaluationCorpusBuilder:
    """Discover and ingest historical intelligence outputs."""

    DEFAULT_SOURCES = [
        "knowledge_service_frontend",
        "fegos_daily_manifest",
        "fegos_observations",
        "hermes_peptide",
    ]

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

    def build(self, output_dir: Path) -> CorpusManifest:
        samples: List[CorpusSample] = []
        sources_used: List[str] = []

        ks_samples = self._ingest_knowledge_service_brief()
        if ks_samples:
            samples.extend(ks_samples)
            sources_used.append("knowledge_service_frontend")

        fegos_samples = self._ingest_fegos_outputs()
        if fegos_samples:
            samples.extend(fegos_samples)
            sources_used.extend(["fegos_daily_manifest", "fegos_observations"])

        manifest = CorpusManifest(
            sample_count=len(samples),
            sources=sorted(set(sources_used)),
            samples=samples,
        )
        self._write_corpus(manifest, output_dir)
        return manifest

    def _ingest_knowledge_service_brief(self) -> List[CorpusSample]:
        path = self.repo_root / "frontend" / "data" / "latest.json"
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get("brief", {}).get("items", [])
        samples: List[CorpusSample] = []
        for index, item in enumerate(items):
            title = str(item.get("title", ""))
            summary = str(item.get("what_changed", ""))
            evidence = summary[:300]
            failure_modes = detect_title_failure_modes(title, evidence)
            quality = "bad" if failure_modes else "good"
            samples.append(CorpusSample(
                sample_id=f"ks-{index:03d}-{title[:20].lower().replace(' ', '_')}",
                source="knowledge_service_frontend",
                captured_at=str(data.get("brief", {}).get("generated_at", "")),
                title=title,
                summary=summary,
                evidence_excerpt=evidence,
                quality_label=quality,
                failure_modes=failure_modes,
                metadata=dict(item),
            ))
        return samples

    def _ingest_fegos_outputs(self) -> List[CorpusSample]:
        fegos_root = self.repo_root.parent / "FEGOS"
        if not fegos_root.exists():
            return []
        samples: List[CorpusSample] = []

        daily_dir = fegos_root / "output" / "daily"
        for manifest_path in sorted(daily_dir.glob("*-manifest.json")):
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            for index, candidate in enumerate(data.get("candidates", [])[:20]):
                title = str(candidate.get("hook", candidate.get("title", f"candidate-{index}")))
                summary = str(candidate.get("body", candidate.get("draft", "")))[:400]
                samples.append(CorpusSample(
                    sample_id=f"fegos-{manifest_path.stem}-{index:02d}",
                    source="fegos_daily_manifest",
                    captured_at=str(data.get("generated_at", manifest_path.stem)),
                    title=title,
                    summary=summary,
                    evidence_excerpt=summary[:200],
                    quality_label="mixed",
                    metadata={"manifest": manifest_path.name},
                ))

        obs_path = fegos_root / "output" / "debug" / "2026-06-30-observations.json"
        if obs_path.exists():
            observations_raw = json.loads(obs_path.read_text(encoding="utf-8"))
            if isinstance(observations_raw, dict):
                observations = list(observations_raw.values())[:30]
            else:
                observations = list(observations_raw)[:30]
            for index, obs in enumerate(observations):
                if isinstance(obs, dict):
                    text = str(obs.get("text", obs.get("content", "")))[:300]
                    metadata = obs
                else:
                    text = str(obs)[:300]
                    metadata = {"raw": text}
                samples.append(CorpusSample(
                    sample_id=f"fegos-obs-{index:03d}",
                    source="fegos_observations",
                    captured_at="2026-06-30",
                    title=text[:80] or f"observation-{index}",
                    summary=text,
                    evidence_excerpt=text[:200],
                    quality_label="mixed",
                    metadata=metadata,
                ))
        return samples

    def _write_corpus(self, manifest: CorpusManifest, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "manifest.json").write_text(
            json.dumps(manifest.to_dict(), indent=2),
            encoding="utf-8",
        )
        samples_dir = output_dir / "samples"
        samples_dir.mkdir(exist_ok=True)
        for sample in manifest.samples or []:
            path = samples_dir / f"{sample.sample_id}.json"
            path.write_text(json.dumps(sample.to_dict(), indent=2), encoding="utf-8")