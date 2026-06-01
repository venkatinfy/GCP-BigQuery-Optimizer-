"""A metadata provider backed by a static dict / JSON fixture.

This keeps the optimizer fully usable offline and in CI (no BigQuery
credentials required) and makes metadata-aware rules deterministically
testable. The JSON shape mirrors :mod:`bq_optimizer.metadata.base`:

```json
{
  "tables": {
    "project.dataset.users": {
      "table_type": "BASE TABLE",
      "row_count": 1000000,
      "size_bytes": 50000000,
      "partition_column": "created_date",
      "clustering_columns": ["country"],
      "columns": {
        "id": {"data_type": "INT64"},
        "email": {"data_type": "STRING"},
        "created_date": {"data_type": "DATE", "is_partitioning_column": true}
      }
    }
  },
  "jobs": [
    {"job_id": "job_123", "state": "DONE",
     "error_reason": "resourcesExceeded",
     "error_message": "Resources exceeded during query execution."}
  ]
}
```
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .base import (
    ColumnMetadata,
    JobMetadata,
    MetadataProvider,
    TableMetadata,
)


class StaticMetadataProvider(MetadataProvider):
    def __init__(self, data: Dict[str, Any]) -> None:
        self._tables: Dict[str, TableMetadata] = {}
        self._by_short: Dict[str, TableMetadata] = {}
        self._jobs: List[JobMetadata] = []
        self._load(data or {})

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    @classmethod
    def from_file(cls, path: Union[str, Path]) -> "StaticMetadataProvider":
        text = Path(path).read_text(encoding="utf-8")
        return cls(json.loads(text))

    def _load(self, data: Dict[str, Any]) -> None:
        for raw_name, raw_tbl in (data.get("tables") or {}).items():
            columns: Dict[str, ColumnMetadata] = {}
            for col_name, raw_col in (raw_tbl.get("columns") or {}).items():
                columns[col_name.lower()] = ColumnMetadata(
                    name=col_name,
                    data_type=raw_col.get("data_type", ""),
                    is_partitioning_column=bool(raw_col.get("is_partitioning_column", False)),
                    is_nullable=bool(raw_col.get("is_nullable", True)),
                )
            partition_column = raw_tbl.get("partition_column")
            if partition_column is None:
                for col in columns.values():
                    if col.is_partitioning_column:
                        partition_column = col.name
                        break
            table = TableMetadata(
                name=raw_name,
                table_type=raw_tbl.get("table_type", "BASE TABLE"),
                row_count=raw_tbl.get("row_count"),
                size_bytes=raw_tbl.get("size_bytes"),
                partition_column=partition_column,
                clustering_columns=list(raw_tbl.get("clustering_columns") or []),
                columns=columns,
            )
            key = raw_name.lower()
            self._tables[key] = table
            short = key.split(".")[-1]
            # Last-write-wins on ambiguous short names; FQN lookups stay exact.
            self._by_short[short] = table

        for raw_job in (data.get("jobs") or []):
            self._jobs.append(JobMetadata(
                job_id=raw_job.get("job_id", ""),
                state=raw_job.get("state", "DONE"),
                error_reason=raw_job.get("error_reason"),
                error_message=raw_job.get("error_message"),
                statement_type=raw_job.get("statement_type"),
                query=raw_job.get("query"),
            ))

    # ------------------------------------------------------------------
    # MetadataProvider
    # ------------------------------------------------------------------
    def get_table(self, name: str) -> Optional[TableMetadata]:
        if not name:
            return None
        key = name.lower()
        if key in self._tables:
            return self._tables[key]
        return self._by_short.get(key.split(".")[-1])

    def get_failed_jobs(self) -> List[JobMetadata]:
        return list(self._jobs)
