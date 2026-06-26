"""Pytest bootstrap helpers for local package imports.

The project does not use a PEP 660 editable install in every environment, so
tests may run with varying working directories. This conftest ensures that the
`src` package root is on ``sys.path`` for both ``knowledge_service`` and
``src.knowledge_service`` style imports.
"""

from pathlib import Path
import sys


_ROOT = Path(__file__).resolve().parent
for _ in range(8):
    if (_ROOT / "src" / "knowledge_service").is_dir():
        _SRC_PATH = str(_ROOT / "src")
        if _SRC_PATH not in sys.path:
            sys.path.insert(0, _SRC_PATH)
        if str(_ROOT) not in sys.path:
            sys.path.insert(0, str(_ROOT))
        break
    parent = _ROOT.parent
    if parent == _ROOT:
        break
    _ROOT = parent
