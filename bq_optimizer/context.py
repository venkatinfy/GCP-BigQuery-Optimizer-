"""Analysis context shared with every rule during a single run."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING

import sqlglot.expressions as exp

if TYPE_CHECKING:  # avoid hard import cycle / optional dependency at runtime
    from .metadata.base import MetadataProvider


@dataclass
class AnalysisContext:
    """Everything a rule may need beyond the single statement it inspects.

    Attributes:
        statements: Every top-level statement parsed from the input script,
            in order. Session-scoped rules (MERGE, redundant updates) reason
            across this list.
        metadata: Optional provider backed by BigQuery ``INFORMATION_SCHEMA``
            (or a static fixture). ``None`` when no metadata was supplied;
            metadata-dependent rules must degrade gracefully in that case.
        raw_sql: The original, unmodified input text.
    """

    statements: List[exp.Expression] = field(default_factory=list)
    metadata: Optional["MetadataProvider"] = None
    raw_sql: str = ""

    @property
    def has_metadata(self) -> bool:
        return self.metadata is not None
