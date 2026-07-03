"""Agent G — Evaluation and benchmarking."""

from .comparison import Runtime3ComparisonHarness
from .metrics import compute_metrics

__all__ = ["Runtime3ComparisonHarness", "compute_metrics"]