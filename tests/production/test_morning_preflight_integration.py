from pathlib import Path


def test_pcc_preflight_invokes_morning_intelligence():
    preflight = Path("/Users/sterlingdigital/bin/pcc-morning-preflight.sh")
    script = Path("/Users/sterlingdigital/Knowledge_Service/bin/morning-intelligence.sh")
    assert preflight.exists()
    assert script.exists()
    text = preflight.read_text(encoding="utf-8")
    assert "morning-intelligence" in text
    assert "Knowledge_Service" in text
    assert "scheduled" in text


def test_morning_intelligence_shell_uses_module_runner():
    script = Path("/Users/sterlingdigital/Knowledge_Service/bin/morning-intelligence.sh")
    text = script.read_text(encoding="utf-8")
    assert "knowledge_service.production.morning" in text
    assert "PYTHONPATH" in text