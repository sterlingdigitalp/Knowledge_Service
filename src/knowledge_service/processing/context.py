"""Processing Context — flows through all pipeline stages"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from ..acquisition.acquisition_bundle import AcquisitionBundle, DocumentRecord
from ..knowledge_object import KnowledgeObject


@dataclass
class StageResult:
    stage_name: str
    success: bool
    confidence_impact: float = 0.0
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class ProcessingContext:
    bundle: Optional[AcquisitionBundle] = None
    document: Optional[DocumentRecord] = None

    raw_content: str = ""
    cleaned_content: str = ""
    normalized_content: str = ""
    normalized_metadata: Dict[str, Any] = field(default_factory=dict)
    extracted_data: Dict[str, Any] = field(default_factory=dict)
    markdown: str = ""
    raw_content_hash: str = ""
    content_hash: str = ""

    title: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    language: Optional[str] = None
    topics: List[str] = field(default_factory=list)
    word_count: int = 0
    confidence: float = 0.0
    evidence_count: int = 0
    citations: List[Dict[str, Any]] = field(default_factory=list)

    chunks: List[Dict[str, Any]] = field(default_factory=list)
    knowledge_objects: List[KnowledgeObject] = field(default_factory=list)

    confidence_adjustments: List[float] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    stage_results: Dict[str, StageResult] = field(default_factory=dict)
