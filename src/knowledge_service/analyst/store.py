"""Persistent store for analyst pipeline artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ..intelligence.state import FileStateStore
from .models import Claim, CorroborationCluster, MorningBrief, ScoredClaim


class AnalystStore:
    CLAIMS_FILE = "analyst/claims.jsonl"
    SCORED_CLAIMS_FILE = "analyst/scored_claims.jsonl"
    CLUSTERS_FILE = "analyst/corroboration_clusters.json"
    BRIEFS_FILE = "analyst/morning_briefs.json"
    RUNS_FILE = "analyst/pipeline_runs.json"

    def __init__(self, state: FileStateStore):
        self.state = state
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        (self.state.root / "analyst").mkdir(parents=True, exist_ok=True)

    def load_claims(self) -> List[Claim]:
        return [Claim.from_dict(row) for row in self.state.read_jsonl(self.CLAIMS_FILE)]

    def save_claims(self, claims: List[Claim]) -> None:
        self.state.write_jsonl(self.CLAIMS_FILE, [claim.to_dict() for claim in claims])

    def append_claims(self, claims: List[Claim]) -> None:
        existing = self.load_claims()
        known = {claim.claim_id for claim in existing}
        for claim in claims:
            if claim.claim_id not in known:
                existing.append(claim)
                known.add(claim.claim_id)
        self.save_claims(existing)

    def load_scored_claims(self) -> List[ScoredClaim]:
        return [ScoredClaim.from_dict(row) for row in self.state.read_jsonl(self.SCORED_CLAIMS_FILE)]

    def save_scored_claims(self, scored: List[ScoredClaim]) -> None:
        self.state.write_jsonl(self.SCORED_CLAIMS_FILE, [item.to_dict() for item in scored])

    def load_clusters(self) -> List[CorroborationCluster]:
        data = self.state.read_json(self.CLUSTERS_FILE, {"clusters": []})
        return [CorroborationCluster.from_dict(item) for item in data.get("clusters", [])]

    def save_clusters(self, clusters: List[CorroborationCluster]) -> None:
        self.state.write_json(self.CLUSTERS_FILE, {"clusters": [cluster.to_dict() for cluster in clusters]})

    def load_briefs(self) -> List[MorningBrief]:
        data = self.state.read_json(self.BRIEFS_FILE, {"briefs": []})
        return [MorningBrief.from_dict(item) for item in data.get("briefs", [])]

    def save_brief(self, brief: MorningBrief) -> None:
        briefs = self.load_briefs()
        briefs.append(brief)
        self.state.write_json(self.BRIEFS_FILE, {"briefs": [item.to_dict() for item in briefs]})

    def latest_brief(self) -> Optional[MorningBrief]:
        briefs = self.load_briefs()
        return briefs[-1] if briefs else None

    def record_run(self, run: Dict[str, Any]) -> None:
        runs = self.state.read_json(self.RUNS_FILE, {"runs": []})
        runs["runs"].append(run)
        self.state.write_json(self.RUNS_FILE, runs)

    def load_runs(self) -> List[Dict[str, Any]]:
        return self.state.read_json(self.RUNS_FILE, {"runs": []}).get("runs", [])

    def summary(self) -> Dict[str, Any]:
        claims = self.load_claims()
        scored = self.load_scored_claims()
        clusters = self.load_clusters()
        briefs = self.load_briefs()
        return {
            "claims": len(claims),
            "scored_claims": len(scored),
            "clusters": len(clusters),
            "briefs": len(briefs),
            "latest_brief_id": briefs[-1].brief_id if briefs else None,
            "runs": len(self.load_runs()),
        }