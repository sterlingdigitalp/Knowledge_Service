from knowledge_service.analyst.synthesis.items.engine import IntelligenceItemEngine
from knowledge_service.analyst.synthesis.themes.discovery import ThemeDiscoveryEngine
from knowledge_service.analyst.synthesis.themes.evolution import ThemeEvolutionEngine
from knowledge_service.intelligence.state import FileStateStore
from knowledge_service.production.conversation.deep_dive_v3 import DeepDiveConversationEngine
from knowledge_service.production.personalization.store import PersonalizationStore

from tests.analyst.synthesis.conftest import build_scored_claims_and_clusters


def _build_item(state_dir):
    scored, clusters = build_scored_claims_and_clusters(state_dir)
    themes = ThemeDiscoveryEngine().discover(scored)
    evolutions = ThemeEvolutionEngine().evaluate(themes, [])
    items = IntelligenceItemEngine().synthesize(scored, themes, clusters, evolutions)
    assert items
    return items[0]


def test_deep_dive_v3_starts_multi_turn_session(phase32_state_dir):
    store = PersonalizationStore(FileStateStore(phase32_state_dir))
    engine = DeepDiveConversationEngine(store)
    item = _build_item(phase32_state_dir)

    session = engine.start(item)

    assert session["session_id"]
    assert session["intelligence_item_id"] == item.item_id
    assert session["title"] == item.title
    assert len(session["messages"]) == 1
    assert session["messages"][0]["role"] == "assistant"
    assert session["suggested_followups"]
    assert session["timeline"]
    assert store.load_sessions()["sessions"][session["session_id"]]


def test_deep_dive_v3_continues_conversation_with_user_turns(phase32_state_dir):
    store = PersonalizationStore(FileStateStore(phase32_state_dir))
    engine = DeepDiveConversationEngine(store)
    item = _build_item(phase32_state_dir)

    session = engine.start(item)
    session_id = session["session_id"]

    continued = engine.continue_conversation(session_id, "Show me the timeline", item)
    messages = continued["messages"]

    assert len(messages) == 3
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "Show me the timeline"
    assert messages[2]["role"] == "assistant"
    assert "timeline" in messages[2]["content"].lower()

    follow_up = engine.continue_conversation(session_id, "What evidence supports this?", item)
    assert len(follow_up["messages"]) == 5
    assert follow_up["messages"][3]["content"] == "What evidence supports this?"
    assert "evidence" in follow_up["messages"][4]["content"].lower()