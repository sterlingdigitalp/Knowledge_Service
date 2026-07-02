"""Publish static Morning Intelligence frontend artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...analyst.synthesis.models import IntelligenceItem
from ..briefing.morning_brief_v3 import IntelligenceBriefV3
from .markdown import render_brief_markdown


@dataclass
class PublishResult:
    latest_html: Path
    latest_md: Path
    latest_json: Path
    archive_dir: Optional[Path] = None
    archived: bool = False
    documents_in_html: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "latest_html": str(self.latest_html),
            "latest_md": str(self.latest_md),
            "latest_json": str(self.latest_json),
            "archive_dir": str(self.archive_dir) if self.archive_dir else None,
            "archived": self.archived,
            "documents_in_html": self.documents_in_html,
        }


@dataclass
class FrontendPublisher:
    frontend_dir: Path
    archive_root: Path = field(default_factory=lambda: Path())
    html_source: Path = field(default_factory=lambda: Path())
    style_source: Path = field(default_factory=lambda: Path())
    app_source: Path = field(default_factory=lambda: Path())

    def __post_init__(self) -> None:
        if not self.archive_root or str(self.archive_root) == ".":
            self.archive_root = self.frontend_dir / "archive"
        if not self.html_source or str(self.html_source) == ".":
            self.html_source = self.frontend_dir / "index.html"
        if not self.style_source or str(self.style_source) == ".":
            self.style_source = self.frontend_dir / "styles.css"
        if not self.app_source or str(self.app_source) == ".":
            self.app_source = self.frontend_dir / "app.js"
        (self.frontend_dir / "data").mkdir(parents=True, exist_ok=True)

    def publish(
        self,
        *,
        brief: IntelligenceBriefV3,
        items: List[IntelligenceItem],
        markdown: str,
        run_summary: Dict[str, Any],
        empty_signal: bool = False,
        prior_documents: Optional[List[Dict[str, Any]]] = None,
    ) -> PublishResult:
        brief_dict = brief.to_dict()
        items_dict = [item.to_dict() for item in items]
        generated_at = brief.generated_at

        current_document = _document_payload(
            document_id=f"run-{brief.brief_id[:12]}",
            label="Today",
            generated_at=generated_at,
            brief=brief_dict,
            markdown=markdown,
            items=items_dict,
        )
        documents = [current_document]
        if prior_documents:
            documents.extend(prior_documents[:6])
        _label_documents(documents)

        payload = {
            "generated_at": generated_at,
            "empty_signal": empty_signal,
            "markdown": markdown,
            "brief": brief_dict,
            "items": items_dict,
            "documents": documents,
            "run_summary": run_summary,
        }

        latest_json = self.frontend_dir / "data" / "latest.json"
        latest_md = self.frontend_dir / "latest.md"
        latest_html = self.frontend_dir / "latest.html"

        latest_json.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        latest_md.write_text(markdown, encoding="utf-8")
        latest_html.write_text(self._render_latest_html(payload), encoding="utf-8")

        archive_dir = self._archive_edition(
            brief=brief_dict,
            markdown=markdown,
            payload=payload,
            run_summary=run_summary,
            generated_at=generated_at,
        )

        return PublishResult(
            latest_html=latest_html,
            latest_md=latest_md,
            latest_json=latest_json,
            archive_dir=archive_dir,
            archived=archive_dir is not None,
            documents_in_html=len(documents),
        )

    def load_prior_documents(self) -> List[Dict[str, Any]]:
        latest_json = self.frontend_dir / "data" / "latest.json"
        if not latest_json.exists():
            return []
        try:
            data = json.loads(latest_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        documents = data.get("documents") or []
        if not isinstance(documents, list):
            return []
        return [doc for doc in documents if isinstance(doc, dict)]

    def _archive_edition(
        self,
        *,
        brief: Dict[str, Any],
        markdown: str,
        payload: Dict[str, Any],
        run_summary: Dict[str, Any],
        generated_at: str,
    ) -> Optional[Path]:
        date_key = _archive_date_key(generated_at)
        archive_dir = self.archive_root / date_key
        archive_dir.mkdir(parents=True, exist_ok=True)
        (archive_dir / "morning.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        (archive_dir / "morning.md").write_text(markdown, encoding="utf-8")
        (archive_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True), encoding="utf-8")
        morning_html = archive_dir / "morning.html"
        morning_html.write_text(self._render_latest_html(payload), encoding="utf-8")
        return archive_dir

    def _render_latest_html(self, payload: Dict[str, Any]) -> str:
        html = self._read_template(self.html_source, "index.html")
        css = self._read_template(self.style_source, "styles.css")
        app = self._read_template(self.app_source, "app.js")
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
                '<script type="module">\n'
                f"{app}\n"
                "</script>"
            ),
        )
        return html

    def _read_template(self, path: Path, label: str) -> str:
        if not path.exists():
            raise FileNotFoundError(
                f"Morning Intelligence frontend template missing ({label}): {path}"
            )
        return path.read_text(encoding="utf-8")


def _document_payload(
    *,
    document_id: str,
    label: str,
    generated_at: str,
    brief: Dict[str, Any],
    markdown: str,
    items: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "id": document_id,
        "label": label,
        "date": _display_date(generated_at),
        "time": _display_time(generated_at),
        "generated_at": generated_at,
        "reading_time": f"{brief.get('reading_time_seconds', 60)} seconds",
        "markdown": markdown,
        "brief": brief,
        "items": items,
    }


def _label_documents(documents: List[Dict[str, Any]]) -> None:
    today = datetime.now().date()
    seen_dates: Dict[str, int] = {}
    for index, document in enumerate(documents):
        generated_at = str(document.get("generated_at") or "")
        try:
            parsed = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
            age = (today - parsed.astimezone(timezone.utc).date()).days
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
            document["label"] = document.get("label") or "Previous date"


def _archive_date_key(generated_at: str) -> str:
    try:
        parsed = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d")
    except ValueError:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _display_date(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.strftime("%A, %B %-d")
    except ValueError:
        return value


def _display_time(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.strftime("%H:%M UTC")
    except ValueError:
        return ""