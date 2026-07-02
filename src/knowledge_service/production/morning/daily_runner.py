"""Phase 6 daily morning intelligence runner — PCC preflight integration."""

from __future__ import annotations

import argparse
import json
import shutil
import socket
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...analyst.models import Claim
from ...analyst.synthesis.models import IntelligenceItem
from ...intelligence.collector import IntelligenceCollector
from ...intelligence.config import load_profiles, save_profiles
from ...intelligence.models import EpisodeStatus, now_iso
from ...intelligence.state import FileStateStore
from ..enhancement import ProductionEnhancementLayer
from ..llm.config import load_llm_config, redact_secrets
from ..pipeline import ProductionIntelligencePipeline
from .env import load_env_local
from .freshness_gate import FreshnessGate, FreshnessReport
from .logger import MorningIntelligenceLogger
from .markdown import build_empty_brief, render_brief_markdown
from .publisher import FrontendPublisher, PublishResult


SERVICE_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_STATE_DIR = SERVICE_ROOT / "state"
DEFAULT_PROFILES = SERVICE_ROOT / "config" / "profiles.json"
DEFAULT_ROUTES = SERVICE_ROOT / "data" / "source_routes.json"
DEFAULT_FRONTEND = SERVICE_ROOT / "frontend"
BOOTSTRAP_STATE = (
    SERVICE_ROOT
    / "runtime_evidence"
    / "phase512_optimization_20260701T074324Z"
    / "state"
)


@dataclass
class MorningRunResult:
    status: str
    started_at: str
    completed_at: str
    duration_seconds: float
    network_ok: bool
    acquisition_status: str
    freshness_report: Dict[str, Any]
    morning_brief_item_count: int
    publish: Dict[str, Any]
    llm_budget: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    degraded: bool = False
    empty_signal: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return redact_secrets({
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
            "network_ok": self.network_ok,
            "acquisition_status": self.acquisition_status,
            "freshness_gate": self.freshness_report,
            "morning_brief_item_count": self.morning_brief_item_count,
            "publish": self.publish,
            "llm_budget": self.llm_budget,
            "errors": list(self.errors),
            "degraded": self.degraded,
            "empty_signal": self.empty_signal,
        })


class MorningIntelligenceRunner:
    """Run the full morning workflow used by PCC preflight and manual commands."""

    def __init__(
        self,
        *,
        service_root: Path | str = SERVICE_ROOT,
        state_dir: Path | str | None = None,
        profiles_path: Path | str | None = None,
        routes_path: Path | str | None = None,
        frontend_dir: Path | str | None = None,
        logger: MorningIntelligenceLogger | None = None,
    ):
        self.service_root = Path(service_root)
        self.state_dir = Path(state_dir or self.service_root / "state")
        self.profiles_path = Path(profiles_path or self.service_root / "config" / "profiles.json")
        self.routes_path = Path(routes_path or self.service_root / "data" / "source_routes.json")
        self.frontend_dir = Path(frontend_dir or self.service_root / "frontend")
        self.logger = logger or MorningIntelligenceLogger()
        self.freshness_gate = FreshnessGate()
        self._last_network_check_detail = "not checked"

    def run(self, *, mode: str = "scheduled") -> MorningRunResult:
        started = time.perf_counter()
        started_at = now_iso()
        self.logger.start(mode=mode)
        load_env_local()
        errors: List[str] = []
        degraded = False

        self._ensure_state_bootstrap()
        network_ok = self._check_network()
        self.logger.section("network", {"ok": network_ok, "detail": self._last_network_check_detail})

        acquisition_summary: Dict[str, Any] = {"status": "skipped", "reason": "network_unavailable"}
        new_episode_ids: List[str] = []
        if network_ok:
            try:
                acquisition_summary, new_episode_ids = self._run_acquisition(mode=mode)
            except Exception as exc:
                acquisition_summary = {"status": "failed", "error": str(exc)}
                errors.append(f"acquisition: {exc}")
                degraded = True
        else:
            degraded = True
            errors.append("network unavailable — using existing corpus")
        self.logger.section("acquisition", acquisition_summary)

        pipeline = ProductionIntelligencePipeline(str(self.state_dir))
        claims_before = {claim.claim_id for claim in pipeline.analyst.store.load_claims()}
        analyst_result = pipeline.analyst.run()
        new_claim_ids = [
            claim.claim_id
            for claim in pipeline.analyst.store.load_claims()
            if claim.claim_id not in claims_before
        ]

        claims_by_id = {claim.claim_id: claim for claim in pipeline.analyst.store.load_claims()}
        ranked_items = pipeline.enhancement.ranking.rank(pipeline.enhancement.synthesis_store.load_items())
        fresh_items, freshness_report = self.freshness_gate.filter_items(
            ranked_items,
            new_episode_ids=new_episode_ids,
            new_claim_ids=new_claim_ids,
            claims_by_id=claims_by_id,
        )
        self.logger.section("freshness_gate", freshness_report.to_dict())

        empty_signal = freshness_report.no_fresh_signal
        if empty_signal:
            production_result = pipeline.enhancement.enhance(
                analyst_result,
                ranked_items=[],
                brief_override=build_empty_brief(pipeline_run_id=analyst_result.run_id),
            )
        else:
            production_result = pipeline.enhancement.enhance(
                analyst_result,
                ranked_items=fresh_items,
            )

        brief = production_result.intelligence_brief_v3
        if brief is None:
            brief = build_empty_brief(pipeline_run_id=analyst_result.run_id)
            empty_signal = True
            degraded = True
            errors.append("brief generation returned empty — published fallback edition")

        brief_items = _brief_linked_items(brief, fresh_items if not empty_signal else [])
        markdown = render_brief_markdown(brief, empty_signal=empty_signal)
        publisher = FrontendPublisher(frontend_dir=self.frontend_dir)
        prior_documents = publisher.load_prior_documents()
        if prior_documents and prior_documents[0].get("label") == "Today":
            prior_documents = prior_documents[1:]

        run_summary = self._build_run_summary(
            started_at=started_at,
            mode=mode,
            network_ok=network_ok,
            acquisition_summary=acquisition_summary,
            analyst_result=analyst_result,
            production_result=production_result,
            freshness_report=freshness_report,
            empty_signal=empty_signal,
            degraded=degraded,
            errors=errors,
        )
        publish_result = publisher.publish(
            brief=brief,
            items=brief_items,
            markdown=markdown,
            run_summary=run_summary,
            empty_signal=empty_signal,
            prior_documents=prior_documents,
        )
        self.logger.section("publish", publish_result.to_dict())

        duration = round(time.perf_counter() - started, 3)
        completed_at = now_iso()
        status = "degraded" if degraded else "success"
        result = MorningRunResult(
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration,
            network_ok=network_ok,
            acquisition_status=str(acquisition_summary.get("status")),
            freshness_report=freshness_report.to_dict(),
            morning_brief_item_count=brief.total_items,
            publish=publish_result.to_dict(),
            llm_budget=production_result.llm_budget,
            errors=errors,
            degraded=degraded,
            empty_signal=empty_signal,
        )
        summary = result.to_dict()
        summary["watched_sources_checked"] = acquisition_summary.get("profiles_checked", 0)
        summary["new_information_events"] = acquisition_summary.get("queued_count", 0)
        summary["new_transcripts"] = acquisition_summary.get("processed_count", 0)
        summary["duplicates_skipped"] = acquisition_summary.get("duplicate_count", 0)
        summary["claims_generated"] = analyst_result.claims_extracted
        summary["themes_generated"] = production_result.themes_renamed
        summary["intelligence_items_generated"] = len(ranked_items)
        summary["grok_calls"] = production_result.llm_budget.get("calls_used", 0)
        summary["cache_hits"] = production_result.llm_budget.get("cache_hits", 0)
        summary["estimated_cost_usd"] = production_result.llm_budget.get("estimated_cost_usd", 0)
        summary["output_files"] = publish_result.to_dict()
        summary["llm_provider"] = load_llm_config().to_public_dict()
        self.logger.finalize(summary)
        try:
            self._persist_run_state(summary)
        except OSError as exc:
            result.errors.append(f"state persistence failed: {exc}")
            result.degraded = True
            result.status = "degraded"
        return result

    def status(self) -> Dict[str, Any]:
        load_env_local()
        state = FileStateStore(self.state_dir)
        last_summary = self.logger.read_last_summary()
        latest_json = self.frontend_dir / "data" / "latest.json"
        latest_exists = {
            "latest.html": (self.frontend_dir / "latest.html").exists(),
            "latest.md": (self.frontend_dir / "latest.md").exists(),
            "latest.json": latest_json.exists(),
        }
        brief_meta: Dict[str, Any] = {}
        brief_meta_error: Optional[str] = None
        if latest_json.exists():
            try:
                data = json.loads(latest_json.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                brief_meta_error = f"latest.json is not valid JSON: {exc}"
            else:
                brief_meta = {
                    "generated_at": data.get("generated_at"),
                    "empty_signal": data.get("empty_signal"),
                    "brief_items": (data.get("brief") or {}).get("total_items"),
                }
        return {
            "service_root": str(self.service_root),
            "state_dir": str(self.state_dir),
            "artifacts": latest_exists,
            "brief": brief_meta,
            "brief_meta_error": brief_meta_error,
            "last_run": last_summary,
            "llm": load_llm_config().to_public_dict(),
        }

    def _ensure_state_bootstrap(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        marker = self.state_dir / "profiles.json"
        if marker.exists():
            return
        if not BOOTSTRAP_STATE.exists():
            if self.profiles_path.exists():
                profiles = load_profiles(self.profiles_path)
                save_profiles(marker, profiles)
            return
        for name in BOOTSTRAP_STATE.iterdir():
            target = self.state_dir / name.name
            if name.is_dir():
                if target.exists():
                    continue
                shutil.copytree(name, target)
            else:
                shutil.copy2(name, target)

    def _check_network(self) -> bool:
        try:
            socket.getaddrinfo("api.x.ai", 443)
        except OSError as exc:
            self._last_network_check_detail = f"dns lookup failed for api.x.ai: {exc}"
            return False
        try:
            with urllib.request.urlopen("https://api.x.ai/v1", timeout=8) as response:
                if response.status in {200, 401, 403, 404}:
                    self._last_network_check_detail = f"api.x.ai reachable (HTTP {response.status})"
                    return True
                self._last_network_check_detail = f"api.x.ai returned unexpected HTTP {response.status}"
                return False
        except Exception as exc:
            try:
                with urllib.request.urlopen("https://podscripts.co", timeout=8) as response:
                    self._last_network_check_detail = (
                        f"api.x.ai unreachable ({type(exc).__name__}: {exc}); "
                        f"fallback podscripts.co reachable (HTTP {response.status})"
                    )
                    return True
            except Exception as fallback_exc:
                self._last_network_check_detail = (
                    f"api.x.ai unreachable ({type(exc).__name__}: {exc}); "
                    f"fallback podscripts.co unreachable ({type(fallback_exc).__name__}: {fallback_exc})"
                )
                return False

    def _run_acquisition(self, *, mode: str) -> tuple[Dict[str, Any], List[str]]:
        profiles = load_profiles(self.profiles_path)
        collector = IntelligenceCollector(
            str(self.state_dir),
            profiles=profiles,
            profile_config_path=str(self.profiles_path),
            route_config_path=str(self.routes_path),
            timeout_ms=30000,
        )
        before_processed = {
            episode.episode_id
            for episode in collector.corpus.episodes()
            if episode.status == EpisodeStatus.PROCESSED
        }
        job = collector.run_once(mode=mode)
        after_processed = [
            episode.episode_id
            for episode in collector.corpus.episodes()
            if episode.status == EpisodeStatus.PROCESSED and episode.episode_id not in before_processed
        ]
        summary = {
            "status": job.status.value,
            "profiles_checked": len(profiles),
            "discovered_count": job.discovered_count,
            "queued_count": job.queued_count,
            "processed_count": job.processed_count,
            "duplicate_count": job.duplicate_count,
            "skipped_count": job.skipped_count,
            "failed_count": job.failed_count,
            "new_episode_ids": after_processed,
        }
        return summary, after_processed

    def _build_run_summary(
        self,
        *,
        started_at: str,
        mode: str,
        network_ok: bool,
        acquisition_summary: Dict[str, Any],
        analyst_result,
        production_result,
        freshness_report: FreshnessReport,
        empty_signal: bool,
        degraded: bool,
        errors: List[str],
    ) -> Dict[str, Any]:
        return redact_secrets({
            "started_at": started_at,
            "completed_at": now_iso(),
            "mode": mode,
            "network_ok": network_ok,
            "acquisition": acquisition_summary,
            "analyst_run_id": analyst_result.run_id,
            "claims_extracted": analyst_result.claims_extracted,
            "freshness_gate": freshness_report.to_dict(),
            "empty_signal": empty_signal,
            "degraded": degraded,
            "errors": errors,
            "production": production_result.to_dict(),
        })

    def _persist_run_state(self, summary: Dict[str, Any]) -> None:
        state = FileStateStore(self.state_dir)
        runs = state.read_json("production/morning_runs.json", {"runs": []})
        runs["runs"].append(summary)
        state.write_json("production/morning_runs.json", runs)


def _brief_linked_items(brief, ranked_items: List[IntelligenceItem]) -> List[IntelligenceItem]:
    if not ranked_items:
        return []
    by_id = {item.item_id: item for item in ranked_items}
    linked = []
    for entry in brief.items:
        item = by_id.get(entry.intelligence_item_id)
        if item is not None:
            linked.append(item)
    return linked or ranked_items[: brief.total_items]


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Knowledge_Service morning intelligence runner")
    parser.add_argument("command", nargs="?", default="run", choices=["run", "status"])
    parser.add_argument("--mode", default="scheduled", choices=["scheduled", "manual"])
    args = parser.parse_args(argv)

    runner = MorningIntelligenceRunner()
    if args.command == "status":
        print(json.dumps(runner.status(), indent=2, sort_keys=True))
        return 0

    result = runner.run(mode=args.mode)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0 if result.status in {"success", "degraded"} else 1


if __name__ == "__main__":
    raise SystemExit(main())