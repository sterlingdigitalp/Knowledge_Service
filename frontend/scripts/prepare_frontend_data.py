"""Prepare static Morning Intelligence frontend data from runtime artifacts.

This script does not run or modify the intelligence pipeline. It embeds the
latest produced brief, brief JSON, and Intelligence Item evidence into the
permanent `frontend/latest.html` entrypoint so bookmarks never need to change.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "runtime_evidence"
FRONTEND = ROOT / "frontend"
HTML_SOURCE = FRONTEND / "index.html"
LATEST_HTML = FRONTEND / "latest.html"
STYLE_SOURCE = FRONTEND / "styles.css"
APP_SOURCE = FRONTEND / "app.js"


def main() -> None:
    run_dirs = brief_run_dirs()
    run_dir = max(run_dirs, key=brief_sort_key)
    documents = [document_payload(path) for path in sorted(run_dirs, key=brief_sort_key, reverse=True)]
    label_documents(documents)
    current = documents[0]

    payload = {
        "generated_from": str(run_dir.relative_to(ROOT)),
        "markdown": current["markdown"],
        "brief": current["brief"],
        "items": current["items"],
        "documents": documents,
    }
    LATEST_HTML.write_text(render_latest_html(payload), encoding="utf-8")
    print(f"Wrote {LATEST_HTML.relative_to(ROOT)} from {run_dir.relative_to(ROOT)}")


def render_latest_html(payload: dict[str, Any]) -> str:
    html = HTML_SOURCE.read_text(encoding="utf-8")
    css = STYLE_SOURCE.read_text(encoding="utf-8")
    app = APP_SOURCE.read_text(encoding="utf-8")
    data_json = json.dumps(payload, sort_keys=True).replace("</", "<\\/")

    html = html.replace(
        '<link rel="stylesheet" href="./styles.css" />',
        f"<style>\n{css}\n</style>",
    )
    html = html.replace(
        '<script src="./app.js" type="module"></script>',
        (
            '<script type="application/json" id="morning-intelligence-data">\n'
            f"{data_json}\n"
            "</script>\n"
            "<script type=\"module\">\n"
            f"{app}\n"
            "</script>"
        ),
    )
    return html


def brief_run_dirs() -> list[Path]:
    candidates = [
        path.parent
        for path in RUNTIME.glob("*/MORNING_INTELLIGENCE_BRIEF.md")
        if (path.parent / "MORNING_INTELLIGENCE_BRIEF.json").exists()
    ]
    if not candidates:
        raise SystemExit("No MORNING_INTELLIGENCE_BRIEF artifacts found.")
    return candidates


def document_payload(run_dir: Path) -> dict[str, Any]:
    brief_path = run_dir / "MORNING_INTELLIGENCE_BRIEF.md"
    brief_json_path = run_dir / "MORNING_INTELLIGENCE_BRIEF.json"
    items_path = run_dir / "state" / "analyst" / "synthesis" / "intelligence_items.json"

    markdown = brief_path.read_text(encoding="utf-8")
    brief = read_json(brief_json_path)
    items_by_id = {str(item.get("item_id") or ""): item for item in merged_items(run_dir, items_path)}
    brief_item_ids = [
        str(entry.get("intelligence_item_id") or "")
        for entry in brief.get("items", [])
        if isinstance(entry, dict)
    ]
    items = [items_by_id[item_id] for item_id in brief_item_ids if item_id in items_by_id]
    generated_at = str(brief.get("generated_at") or "")
    return {
        "id": run_dir.name,
        "label": display_date(generated_at) if generated_at else "Previous date",
        "date": display_date(generated_at) if generated_at else run_dir.name,
        "time": display_time(generated_at) if generated_at else "",
        "generated_at": generated_at,
        "reading_time": f"{brief.get('reading_time_seconds', 60)} seconds",
        "markdown": markdown,
        "brief": brief,
        "items": items,
    }


def label_documents(documents: list[dict[str, Any]]) -> None:
    seen_dates: dict[str, int] = {}
    today = datetime.now().date()
    for index, document in enumerate(documents):
        generated_at = str(document.get("generated_at") or "")
        try:
            parsed = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
            age = (today - parsed.date()).days
            date_key = parsed.date().isoformat()
        except ValueError:
            parsed = None
            age = 999
            date_key = generated_at

        seen_dates[date_key] = seen_dates.get(date_key, 0) + 1
        if index == 0 and age == 0:
            document["label"] = "Today"
        elif age == 1:
            document["label"] = "Yesterday"
        elif parsed and seen_dates[date_key] > 1:
            document["label"] = f"{parsed.strftime('%b %-d')} · {document.get('time', '')}"
        elif parsed:
            document["label"] = parsed.strftime("%b %-d")
        else:
            document["label"] = "Previous date"


def brief_sort_key(path: Path) -> str:
    brief = read_json(path / "MORNING_INTELLIGENCE_BRIEF.json")
    return str(brief.get("generated_at") or path.name)


def normalize_items(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        data = data.get("items", [])
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def merged_items(run_dir: Path, items_path: Path) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for path in [
        run_dir / "raw" / "heuristic_items.json",
        run_dir / "raw" / "xai_items.json",
        items_path,
    ]:
        if not path.exists():
            continue
        for item in normalize_items(read_json(path)):
            item_id = str(item.get("item_id") or "")
            if item_id:
                by_id[item_id] = item
    return list(by_id.values())


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def display_date(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    return parsed.strftime("%A, %B %-d")


def display_time(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return ""
    return parsed.strftime("%H:%M UTC")


if __name__ == "__main__":
    main()
