"""Planning Layer — Interfaces

Defines the Planner interface and AcquisitionPlan data structure.
The Planning Layer knows only provider capabilities and interfaces.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Protocol
from ..interfaces.provider import ProviderType


@dataclass
class PlanStep:
    """A single step in an acquisition plan."""
    step_id: str
    provider_type: ProviderType
    target: str
    options: Dict[str, Any] = field(default_factory=dict)
    fallback_strategy: str = "skip"  # skip, retry, alternative
    max_retries: int = 1


@dataclass
class AcquisitionPlan:
    """An acquisition plan produced by the Planner.

    Contains a sequence of steps to execute.
    The AcquisitionExecutor follows these steps to produce an AcquisitionBundle.
    """
    plan_id: str
    request_id: str
    query: str
    steps: List[PlanStep] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_step(self, step: PlanStep) -> None:
        self.steps.append(step)

    def step_count(self) -> int:
        return len(self.steps)


class Planner(Protocol):
    """Protocol for Planner implementations.

    Accepts a knowledge request and produces an acquisition plan.
    """

    def plan(self, query: str, request_id: str) -> AcquisitionPlan:
        """Analyze a query and produce an acquisition plan."""
        ...
