"""Acquisition Bundle Implementation - Phase 1.1B"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime


@dataclass
class ExecutionRecord:
    """Record of a provider execution"""
    step_id: str
    provider_name: str
    provider_type: str  # search, crawl, api, rss, file_processor, database
    target: str
    status: str  # success, partial, failed, cached
    raw_response: Optional[Dict[str, Any]] = None
    response_metadata: Dict[str, Any] = field(default_factory=dict)
    latency_ms: int = 0
    error_code: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class DocumentRecord:
    """Record of an acquired document"""
    document_id: str
    url: str
    provider_name: str
    content_type: str
    raw_content: str
    content_size_bytes: int
    acquired_at: str  # ISO 8601 timestamp


@dataclass
class Warning:
    """Acquisition warning"""
    code: str
    message: str
    affected_steps: List[str] = field(default_factory=list)


@dataclass
class Error:
    """Acquisition error"""
    code: str
    message: str
    severity: str  # critical, warning, info


@dataclass
class AcquisitionBundle:
    """Canonical acquisition bundle passed from Acquisition Layer to Processing Layer"""
    
    request_id: str
    plan_id: str
    acquisition_timestamp: str  # ISO 8601 timestamp
    
    provider_executions: List[ExecutionRecord] = field(default_factory=list)
    discovered_urls: List[str] = field(default_factory=list)
    acquired_documents: List[DocumentRecord] = field(default_factory=list)
    
    total_duration_ms: int = 0
    search_duration_ms: int = 0
    crawl_duration_ms: int = 0
    
    providers_queried: int = 0
    providers_successful: int = 0
    providers_failed: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    
    warnings: List[Warning] = field(default_factory=list)
    errors: List[Error] = field(default_factory=list)
    
    def add_execution_record(self, record: ExecutionRecord):
        """Add an execution record to the bundle"""
        self.provider_executions.append(record)
        if record.status == "success" or record.status == "partial":
            self.providers_successful += 1
        elif record.status == "failed":
            self.providers_failed += 1
        self.providers_queried += 1
        
        if record.provider_type == "search":
            self.search_duration_ms += record.latency_ms
        elif record.provider_type == "crawl":
            self.crawl_duration_ms += record.latency_ms
    
    def add_document(self, document: DocumentRecord):
        """Add an acquired document to the bundle"""
        self.acquired_documents.append(document)
    
    def add_discovered_url(self, url: str):
        """Add a discovered URL to the bundle"""
        if url not in self.discovered_urls:
            self.discovered_urls.append(url)
    
    def add_warning(self, warning: Warning):
        """Add a warning to the bundle"""
        self.warnings.append(warning)
    
    def add_error(self, error: Error):
        """Add an error to the bundle"""
        self.errors.append(error)
