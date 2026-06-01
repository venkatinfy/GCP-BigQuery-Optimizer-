"""Metadata model and provider interface.

These dataclasses mirror the columns exposed by BigQuery's
``INFORMATION_SCHEMA`` views so that the optimizer's metadata-aware rules can
make the same decisions a human reviewer would when inspecting catalog data.
See :mod:`bq_optimizer.metadata.schema` for the exact queries used to populate
them from a live project.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ColumnMetadata:
    """A single column, sourced from ``INFORMATION_SCHEMA.COLUMNS``."""

    name: str
    data_type: str = ""                       # e.g. "STRING", "INT64", "TIMESTAMP"
    is_partitioning_column: bool = False
    is_nullable: bool = True

    @property
    def is_string(self) -> bool:
        return self.data_type.upper() in {"STRING", "BYTES"}

    @property
    def is_integer(self) -> bool:
        return self.data_type.upper() in {"INT64", "INTEGER", "NUMERIC", "BIGNUMERIC"}


@dataclass
class TableMetadata:
    """A table/view, sourced from ``INFORMATION_SCHEMA.TABLES`` (+ storage)."""

    name: str
    table_type: str = "BASE TABLE"            # BASE TABLE | EXTERNAL | VIEW | MATERIALIZED VIEW
    row_count: Optional[int] = None
    size_bytes: Optional[int] = None
    partition_column: Optional[str] = None
    clustering_columns: List[str] = field(default_factory=list)
    columns: Dict[str, ColumnMetadata] = field(default_factory=dict)

    @property
    def is_external(self) -> bool:
        return self.table_type.upper() == "EXTERNAL"

    def column(self, name: str) -> Optional[ColumnMetadata]:
        return self.columns.get(name.lower())


@dataclass
class JobMetadata:
    """A query job, sourced from ``INFORMATION_SCHEMA.JOBS_BY_PROJECT``."""

    job_id: str
    state: str = "DONE"
    error_reason: Optional[str] = None        # e.g. "resourcesExceeded"
    error_message: Optional[str] = None
    statement_type: Optional[str] = None
    query: Optional[str] = None

    # Error reasons BigQuery emits when a job is killed for capacity/resource limits.
    RESOURCE_ERROR_REASONS = {
        "resourcesExceeded",
        "rateLimitExceeded",
        "quotaExceeded",
        "billingTierLimitExceeded",
    }
    RESOURCE_ERROR_KEYWORDS = (
        "resources exceeded",
        "exceeded resources",
        "shuffle",
        "memory",
        "too many",
        "exceeded quota",
        "exceeded rate limits",
        "slots",
    )

    @property
    def failed_on_resources(self) -> bool:
        reason = (self.error_reason or "")
        if reason in self.RESOURCE_ERROR_REASONS:
            return True
        blob = f"{reason} {self.error_message or ''}".lower()
        return any(k in blob for k in self.RESOURCE_ERROR_KEYWORDS)


class MetadataProvider(ABC):
    """Resolves catalog metadata for tables and recent jobs."""

    @abstractmethod
    def get_table(self, name: str) -> Optional[TableMetadata]:
        """Return metadata for a table by fully-qualified or short name."""

    def get_failed_jobs(self) -> List[JobMetadata]:
        """Return recent failed jobs. Empty when unsupported/unavailable."""
        return []
