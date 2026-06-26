"""Storage repositories package."""

from .knowledge_repository import KnowledgeRepository
from .source_entry import SourceEntry

__all__ = ["KnowledgeRepository", "SourceRepository", "SourceEntry"]


def __getattr__(name: str):
    if name == "SourceRepository":
        from .source_repository import SourceRepository
        return SourceRepository
    raise AttributeError(name)
