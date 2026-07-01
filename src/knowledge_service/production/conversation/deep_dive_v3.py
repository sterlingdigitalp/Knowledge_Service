"""Deep Dive v3 — multi-turn analyst conversation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ...analyst.synthesis.models import IntelligenceItem
from ...intelligence.models import now_iso, stable_id
from ..llm.provider import ConversationRequest
from ..llm.registry import get_llm_provider
from ..personalization.store import PersonalizationStore


class DeepDiveConversationEngine:
    """Analyst-quality multi-turn conversations over Intelligence Items."""

    def __init__(self, store: PersonalizationStore):
        self.store = store
        self.llm = get_llm_provider()

    def start(self, item: IntelligenceItem) -> Dict[str, Any]:
        session_id = stable_id("conversation", item.item_id, now_iso())
        request = ConversationRequest(
            intelligence_item_id=item.item_id,
            title=item.title,
            executive_summary=item.executive_summary,
            user_message="Tell me more",
            evidence=item.supporting_evidence,
        )
        result = self.llm.converse(request)
        followups = self.llm.suggested_followups(
            title=item.title,
            executive_summary=item.executive_summary,
            contradiction_count=item.contradiction_count,
            corroboration_count=item.corroboration_count,
        )
        session = {
            "session_id": session_id,
            "intelligence_item_id": item.item_id,
            "title": item.title,
            "started_at": now_iso(),
            "llm_provider": result.provider or self.llm.name,
            "last_response_id": result.response_id,
            "messages": [
                {"role": "assistant", "content": result.text, "timestamp": now_iso()},
            ],
            "suggested_followups": followups,
            "timeline": _timeline(item),
            "competing_viewpoints": item.contradictions,
            "watch_points": _watch_points(item),
        }
        self._save_session(session)
        return session

    def continue_conversation(self, session_id: str, user_message: str, item: IntelligenceItem) -> Dict[str, Any]:
        sessions = self.store.load_sessions().get("sessions", {})
        session = sessions.get(session_id)
        if session is None:
            session = self.start(item)
            session_id = session["session_id"]

        history = session.get("messages", [])
        request = ConversationRequest(
            intelligence_item_id=item.item_id,
            title=item.title,
            executive_summary=item.executive_summary,
            user_message=user_message,
            conversation_history=history,
            evidence=item.supporting_evidence,
            previous_response_id=session.get("last_response_id"),
        )
        result = self.llm.converse(request)
        history.append({"role": "user", "content": user_message, "timestamp": now_iso()})
        history.append({"role": "assistant", "content": result.text, "timestamp": now_iso()})
        session["last_response_id"] = result.response_id or session.get("last_response_id")
        session["llm_provider"] = result.provider or session.get("llm_provider", self.llm.name)
        session["messages"] = history
        session["updated_at"] = now_iso()
        self._save_session(session)
        return session

    def _save_session(self, session: Dict[str, Any]) -> None:
        data = self.store.load_sessions()
        sessions = data.setdefault("sessions", {})
        sessions[session["session_id"]] = session
        self.store.save_sessions(data)


def _timeline(item: IntelligenceItem) -> List[Dict[str, Any]]:
    return [
        {
            "timestamp_label": evidence.get("timestamp_label"),
            "speaker": evidence.get("speaker"),
            "source": evidence.get("source"),
            "event": str(evidence.get("excerpt", ""))[:140],
        }
        for evidence in item.supporting_evidence
    ]


def _watch_points(item: IntelligenceItem) -> List[str]:
    points = []
    if item.corroboration_count < 2:
        points.append("Watch for additional independent confirmation.")
    if item.contradiction_count:
        points.append("Watch whether opposing voices reconcile or diverge further.")
    if item.theme_evolution and item.theme_evolution.state.value in {"strengthening", "new"}:
        points.append("Theme is still accelerating — monitor follow-on commentary.")
    if not points:
        points.append("Watch for policy, product, or capital allocation follow-through.")
    return points