# Runtime Scheduler

The Runtime Scheduler runs collection without manual transcript retrieval.

## Modes
- Manual: `RuntimeScheduler.run_manual()`
- Scheduled once: `RuntimeScheduler.run_scheduled_once()`
- Daemon: `RuntimeScheduler.run_daemon(max_iterations=None)`

## Job State
Collection jobs track:
- profile IDs
- queued/discovered/processed/duplicate/skipped/failed counts
- current step
- errors
- performance timings

## Graceful Recovery
Scheduler state is persisted in `state/scheduler.json`. Running a new scheduler instance on the same state directory resumes with existing dedupe hashes, preventing repeated transcript ingestion.

## Continuous Operation
Daemon mode repeatedly executes scheduled collection at the configured interval and handles `SIGINT`/`SIGTERM` by requesting a clean stop.

## Certification Evidence
The Phase 3 certification runs a scheduled pass, creates a new collector and scheduler over the same state directory, and verifies the restart pass processes `0` episodes and detects `4` duplicates.
