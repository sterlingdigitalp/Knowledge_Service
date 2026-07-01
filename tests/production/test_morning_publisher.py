import json
from pathlib import Path

from knowledge_service.production.morning.markdown import build_empty_brief, render_brief_markdown
from knowledge_service.production.morning.publisher import FrontendPublisher


def test_publisher_writes_latest_and_archive(tmp_path: Path):
    frontend = tmp_path / "frontend"
    frontend.mkdir(parents=True, exist_ok=True)
    for name in ["index.html", "styles.css", "app.js"]:
        src = Path(__file__).resolve().parents[2] / "frontend" / name
        (frontend / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    brief = build_empty_brief(pipeline_run_id="test-run")
    markdown = render_brief_markdown(brief, empty_signal=True)
    publisher = FrontendPublisher(frontend_dir=frontend)
    result = publisher.publish(
        brief=brief,
        items=[],
        markdown=markdown,
        run_summary={"status": "success"},
        empty_signal=True,
    )

    assert result.latest_html.exists()
    assert result.latest_md.exists()
    assert result.latest_json.exists()
    assert result.archive_dir is not None
    assert (result.archive_dir / "morning.html").exists()
    assert (result.archive_dir / "morning.md").exists()
    assert (result.archive_dir / "morning.json").exists()
    assert (result.archive_dir / "run_summary.json").exists()

    payload = json.loads(result.latest_json.read_text(encoding="utf-8"))
    assert payload["empty_signal"] is True
    assert "Morning Intelligence" in result.latest_html.read_text(encoding="utf-8")