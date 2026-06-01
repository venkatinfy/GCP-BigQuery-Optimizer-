"""Metadata providers backed by BigQuery INFORMATION_SCHEMA (or static JSON)."""

from .base import (
    ColumnMetadata,
    JobMetadata,
    MetadataProvider,
    TableMetadata,
)
from .static import StaticMetadataProvider

__all__ = [
    "ColumnMetadata",
    "JobMetadata",
    "MetadataProvider",
    "TableMetadata",
    "StaticMetadataProvider",
]
