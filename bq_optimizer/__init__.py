"""BigQuery Query Optimizer — rule-based SQL analysis and optimization."""

from .analyzer import QueryAnalyzer, AnalysisResult
from .context import AnalysisContext
from .rules.base import Finding, Severity
from .metadata import (
    MetadataProvider,
    StaticMetadataProvider,
    TableMetadata,
    ColumnMetadata,
    JobMetadata,
)

__all__ = [
    "QueryAnalyzer",
    "AnalysisResult",
    "AnalysisContext",
    "Finding",
    "Severity",
    "MetadataProvider",
    "StaticMetadataProvider",
    "TableMetadata",
    "ColumnMetadata",
    "JobMetadata",
]
__version__ = "0.2.0"
