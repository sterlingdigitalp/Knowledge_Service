"""Phase 5 Production Personal Intelligence Analyst."""

__all__ = ["ProductionIntelligencePipeline"]


def __getattr__(name: str):
    if name == "ProductionIntelligencePipeline":
        from .pipeline import ProductionIntelligencePipeline
        return ProductionIntelligencePipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")