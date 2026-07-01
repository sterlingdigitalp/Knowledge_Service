import os
from pathlib import Path
from unittest.mock import patch

import pytest

from knowledge_service.production.llm.registry import get_llm_provider


def test_missing_api_key_uses_heuristic_provider(tmp_path: Path):
    env = {key: value for key, value in os.environ.items() if key not in {"XAI_API_KEY", "OPENAI_API_KEY"}}
    with patch.dict(os.environ, env, clear=True):
        provider = get_llm_provider(state_dir=str(tmp_path))
    assert provider.name in {"analyst_heuristic", "xai_responses"}
    if not os.environ.get("XAI_API_KEY"):
        assert provider.name == "analyst_heuristic"