"""Optional live metadata provider backed by BigQuery INFORMATION_SCHEMA.

Requires the ``bigquery`` extra::

    pip install "bq-optimizer[bigquery]"

The dependency is imported lazily so the core tool stays dependency-light and
fully usable offline via :class:`StaticMetadataProvider`.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .base import (
    ColumnMetadata,
    JobMetadata,
    MetadataProvider,
    TableMetadata,
)
from . import schema


class BigQueryMetadataProvider(MetadataProvider):
    def __init__(
        self,
        project: str,
        datasets: List[str],
        region: str = "region-us",
        lookback_days: int = 7,
        job_limit: int = 200,
        client: Optional[object] = None,
    ) -> None:
        self.project = project
        self.datasets = datasets
        self.region = region
        self.lookback_days = lookback_days
        self.job_limit = job_limit
        self._client = client
        self._tables: Optional[Dict[str, TableMetadata]] = None
        self._jobs: Optional[List[JobMetadata]] = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from google.cloud import bigquery  # type: ignore
        except ImportError as exc:  # pragma: no cover - exercised only without extra
            raise RuntimeError(
                "BigQueryMetadataProvider requires the 'bigquery' extra. "
                "Install it with: pip install \"bq-optimizer[bigquery]\""
            ) from exc
        self._client = bigquery.Client(project=self.project)
        return self._client

    def _load_tables(self) -> Dict[str, TableMetadata]:
        if self._tables is not None:
            return self._tables
        client = self._get_client()
        tables: Dict[str, TableMetadata] = {}

        def fqn(row) -> str:
            return f"{row['table_catalog']}.{row['table_schema']}.{row['table_name']}".lower()

        for dataset in self.datasets:
            ds_ref = f"{self.project}.{dataset}" if "." not in dataset else dataset
            for row in client.query(schema.TABLES_QUERY.format(dataset=ds_ref)).result():
                tables.setdefault(fqn(row), TableMetadata(name=fqn(row))).table_type = row["table_type"]
            for row in client.query(schema.TABLE_STORAGE_QUERY.format(dataset=ds_ref)).result():
                t = tables.setdefault(fqn(row), TableMetadata(name=fqn(row)))
                t.row_count = row["total_rows"]
                t.size_bytes = row["total_logical_bytes"]
            for row in client.query(schema.COLUMNS_QUERY.format(dataset=ds_ref)).result():
                t = tables.setdefault(fqn(row), TableMetadata(name=fqn(row)))
                is_part = str(row["is_partitioning_column"]).upper() == "YES"
                t.columns[row["column_name"].lower()] = ColumnMetadata(
                    name=row["column_name"],
                    data_type=row["data_type"],
                    is_partitioning_column=is_part,
                    is_nullable=str(row["is_nullable"]).upper() == "YES",
                )
                if is_part:
                    t.partition_column = row["column_name"]

        self._tables = tables
        return tables

    def get_table(self, name: str) -> Optional[TableMetadata]:
        if not name:
            return None
        tables = self._load_tables()
        key = name.lower()
        if key in tables:
            return tables[key]
        short = key.split(".")[-1]
        for fq, tbl in tables.items():
            if fq.split(".")[-1] == short:
                return tbl
        return None

    def get_failed_jobs(self) -> List[JobMetadata]:
        if self._jobs is not None:
            return self._jobs
        client = self._get_client()
        query = schema.JOBS_FAILURES_QUERY.format(
            region=self.region, lookback_days=self.lookback_days, limit=self.job_limit
        )
        jobs: List[JobMetadata] = []
        for row in client.query(query).result():
            jobs.append(JobMetadata(
                job_id=row["job_id"],
                state=row["state"],
                error_reason=row.get("error_reason"),
                error_message=row.get("error_message"),
                statement_type=row.get("statement_type"),
                query=row.get("query"),
            ))
        self._jobs = jobs
        return jobs
