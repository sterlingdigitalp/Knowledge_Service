"""Provider Interface Definitions - Phase 0 Architecture"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
import time


class ProviderType(Enum):
    SEARCH = "search"
    CRAWL = "crawl"
    API = "api"
    RSS = "rss"
    FILE_PROCESSOR = "file_processor"
    DATABASE = "database"


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class InitResult:
    """Provider initialization result"""
    name: str
    version: Optional[str] = None
    capabilities: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderRequest:
    """Standardized provider request"""
    target: str
    provider_type: ProviderType
    options: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderResponse:
    """Standardized provider response"""
    content: Optional[str] = None
    content_type: str = "application/octet-stream"
    status_code: int = 200
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional['ProviderError'] = None


@dataclass
class ProviderError:
    """Standardized provider error"""
    code: str
    message: str
    provider_specific_code: Optional[str] = None
    retryable: bool = True
    recoverable: bool = True


@dataclass
class HealthCheckResult:
    """Provider health check result"""
    status: HealthStatus
    last_check_time: float = field(default_factory=time.time)
    degradation_reason: Optional[str] = None


class Provider:
    """Base Provider Interface - All providers must implement these methods"""
    
    def initialize(self, config: Dict[str, Any]) -> InitResult:
        """Initialize provider with configuration"""
        raise NotImplementedError
    
    def execute(self, request: ProviderRequest) -> ProviderResponse:
        """Execute provider operation"""
        raise NotImplementedError
    
    def health(self) -> HealthCheckResult:
        """Check provider health status"""
        raise NotImplementedError
    
    def shutdown(self) -> None:
        """Gracefully shut down provider"""
        pass
    
    @property
    def name(self) -> str:
        """Provider instance name"""
        raise NotImplementedError
    
    @property
    def capabilities(self) -> Dict[str, Any]:
        """Provider capabilities declaration"""
        raise NotImplementedError
