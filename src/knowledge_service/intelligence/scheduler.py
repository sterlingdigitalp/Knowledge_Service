"""Runtime scheduler for continuous profile-driven collection."""

from __future__ import annotations

import signal
import time
from typing import Any, Dict, Optional

from .collector import IntelligenceCollector
from .models import CollectionJob, now_iso


class RuntimeScheduler:
    def __init__(self, collector: IntelligenceCollector, interval_seconds: int = 3600):
        self.collector = collector
        self.interval_seconds = interval_seconds
        self._stop_requested = False
        self.state = collector.state

    def run_manual(self) -> CollectionJob:
        return self.collector.run_once(mode="manual")

    def run_scheduled_once(self) -> CollectionJob:
        return self.collector.run_once(mode="scheduled")

    def run_daemon(self, max_iterations: Optional[int] = None) -> Dict[str, Any]:
        self._stop_requested = False
        self._install_signal_handlers()
        iterations = 0
        jobs = []
        started_at = now_iso()
        while not self._stop_requested:
            jobs.append(self.run_scheduled_once().to_dict())
            iterations += 1
            self._write_scheduler_state("sleeping", iterations, jobs)
            if max_iterations is not None and iterations >= max_iterations:
                break
            deadline = time.time() + self.interval_seconds
            while time.time() < deadline and not self._stop_requested:
                time.sleep(min(0.25, max(0.0, deadline - time.time())))
        final = {
            "status": "stopped" if self._stop_requested else "completed",
            "started_at": started_at,
            "stopped_at": now_iso(),
            "interval_seconds": self.interval_seconds,
            "iterations": iterations,
            "jobs": jobs,
        }
        self.state.write_json("scheduler.json", final)
        return final

    def request_stop(self) -> None:
        self._stop_requested = True

    def inspect(self) -> Dict[str, Any]:
        return self.state.read_json("scheduler.json", {
            "status": "idle",
            "interval_seconds": self.interval_seconds,
            "iterations": 0,
            "jobs": [],
        })

    def _write_scheduler_state(self, status: str, iterations: int, jobs: list[Dict[str, Any]]) -> None:
        self.state.write_json("scheduler.json", {
            "status": status,
            "updated_at": now_iso(),
            "interval_seconds": self.interval_seconds,
            "iterations": iterations,
            "jobs": jobs,
        })

    def _install_signal_handlers(self) -> None:
        try:
            signal.signal(signal.SIGTERM, lambda *_args: self.request_stop())
            signal.signal(signal.SIGINT, lambda *_args: self.request_stop())
        except Exception:
            pass
