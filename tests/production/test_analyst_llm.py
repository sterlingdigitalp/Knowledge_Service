from knowledge_service.production.llm.analyst_provider import AnalystLLMProvider
from knowledge_service.production.llm.provider import SummaryRequest, ThemeNamingRequest
from knowledge_service.production.llm.registry import configure_llm, get_llm_provider


def test_theme_naming_produces_analyst_style_titles():
    provider = AnalystLLMProvider()

    inference = provider.name_theme(ThemeNamingRequest(
        keywords=["inference", "gpu", "datacenter", "cost"],
        entities=["NVIDIA"],
        sample_claims=["Inference costs per token are climbing as clusters scale."],
        sources=["AI Podcast"],
        speakers=["Sam Altman"],
    ))
    agents = provider.name_theme(ThemeNamingRequest(
        keywords=["agent", "autonomous", "workflow", "tools"],
        entities=["OpenAI"],
        sample_claims=["Teams are shipping autonomous agents that call APIs."],
        sources=["Operator Roundtable"],
        speakers=["Operator"],
    ))
    glp1 = provider.name_theme(ThemeNamingRequest(
        keywords=["glp-1", "ozempic", "metabolic", "clinical"],
        entities=["Novo Nordisk"],
        sample_claims=["GLP-1 adoption is reshaping metabolic medicine."],
        sources=["Health Brief"],
        speakers=["Researcher"],
    ))

    assert inference == "Inference Economics"
    assert agents == "Enterprise AI Agents"
    assert glp1 == "GLP-1 Competitive Landscape"


def test_executive_summary_uses_analyst_report_structure():
    provider = AnalystLLMProvider()
    summary = provider.executive_summary(SummaryRequest(
        theme_label="inference economics",
        title="Inference Economics",
        keywords=["inference", "gpu"],
        entities=["NVIDIA"],
        sources=["Podcast A", "Podcast B"],
        speakers=["Speaker A", "Speaker B"],
        claim_excerpts=["Inference unit economics are deteriorating as demand scales."],
        novelty_classification="new",
        importance_band="high",
        corroboration_count=2,
        contradictions=0,
        theme_evolution="Theme is strengthening across sources.",
    ))

    assert "independent sources" in summary.lower()
    assert "core signal" in summary.lower()
    assert "why it matters" in summary.lower()
    assert "why now" in summary.lower()
    assert "what to watch next" in summary.lower()
    assert "Inference Economics" in summary or "inference" in summary.lower()


def test_llm_provider_registry_defaults_to_analyst_heuristic():
    provider = configure_llm("analyst_heuristic")
    assert provider.name == "analyst_heuristic"
    assert get_llm_provider().name == "analyst_heuristic"