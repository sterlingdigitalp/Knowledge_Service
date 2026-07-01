from datetime import datetime, timedelta, timezone

from knowledge_service.intelligence.state import FileStateStore
from knowledge_service.production.scheduler.brief_scheduler import (
    SCHEDULE_DAILY,
    SCHEDULE_MANUAL,
    SCHEDULE_WEEKDAYS,
    MorningBriefScheduler,
)


def _scheduler(tmp_path) -> MorningBriefScheduler:
    return MorningBriefScheduler(FileStateStore(tmp_path))


def test_daily_schedule_runs_once_per_day_after_hour(tmp_path):
    scheduler = _scheduler(tmp_path)
    scheduler.configure(schedule=SCHEDULE_DAILY, hour_utc=12, enabled=True)

    # record_run() stamps history with the real UTC date, so anchor the test on "today".
    today_noon = datetime.now(timezone.utc).replace(minute=30, second=0, microsecond=0)
    if today_noon.hour < 12:
        today_noon = today_noon.replace(hour=12)

    assert scheduler.should_run(today_noon) is True

    scheduler.record_run("run-1")
    assert scheduler.should_run(today_noon) is False

    next_day = today_noon + timedelta(days=1)
    assert scheduler.should_run(next_day) is True


def test_weekdays_schedule_skips_weekends(tmp_path):
    scheduler = _scheduler(tmp_path)
    scheduler.configure(schedule=SCHEDULE_WEEKDAYS, hour_utc=8, enabled=True)

    saturday = datetime(2026, 7, 4, 9, 0, tzinfo=timezone.utc)
    sunday = datetime(2026, 7, 5, 9, 0, tzinfo=timezone.utc)
    monday = datetime(2026, 7, 6, 9, 0, tzinfo=timezone.utc)

    assert scheduler.should_run(saturday) is False
    assert scheduler.should_run(sunday) is False
    assert scheduler.should_run(monday) is True


def test_manual_schedule_never_auto_runs_and_inspect_reports_state(tmp_path):
    scheduler = _scheduler(tmp_path)
    scheduler.configure(schedule=SCHEDULE_MANUAL, hour_utc=0, enabled=True)

    now = datetime(2026, 6, 30, 15, 0, tzinfo=timezone.utc)
    assert scheduler.should_run(now) is False

    manual_entry = scheduler.record_run("manual-run", manual=True)
    report = scheduler.inspect()

    assert manual_entry["manual"] is True
    assert report["config"]["schedule"] == SCHEDULE_MANUAL
    assert report["history_count"] == 1
    assert report["last_run"]["run_id"] == "manual-run"
    assert report["should_run_now"] is False