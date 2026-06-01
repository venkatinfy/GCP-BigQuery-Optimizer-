"""BigQuery Query Optimizer — rule-based SQL analysis and optimization."""

from .analyzer import QueryAnalyzer, AnalysisResult
from .rules.base import Finding, Severity

__all__ = ["QueryAnalyzer", "AnalysisResult", "Finding", "Severity"]
__version__ = "0.1.0"
