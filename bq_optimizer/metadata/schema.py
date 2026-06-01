"""Canonical ``INFORMATION_SCHEMA`` queries used to populate metadata.

These are the exact, enterprise-standard queries the optional live provider
issues against a BigQuery project/region. They are exposed here (rather than
buried in the client) so they can be reviewed, reused in dashboards, or run by
hand to produce the static JSON fixture consumed by
:class:`bq_optimizer.metadata.static.StaticMetadataProvider`.

``{region}`` is a region-qualified dataset such as ``region-us`` and
``{dataset}`` is a fully-qualified ``project.dataset`` reference.
"""

# Column data types + partitioning flags -> ColumnMetadata.
COLUMNS_QUERY = """
SELECT
  table_catalog, table_schema, table_name,
  column_name, data_type, is_nullable,
  is_partitioning_column
FROM `{dataset}`.INFORMATION_SCHEMA.COLUMNS
"""

# Table type (BASE TABLE / VIEW / EXTERNAL ...) -> TableMetadata.table_type.
TABLES_QUERY = """
SELECT
  table_catalog, table_schema, table_name, table_type
FROM `{dataset}`.INFORMATION_SCHEMA.TABLES
"""

# Logical row counts and byte sizes -> join-ordering and large-scan decisions.
TABLE_STORAGE_QUERY = """
SELECT
  table_catalog, table_schema, table_name,
  total_rows, total_logical_bytes
FROM `{dataset}`.INFORMATION_SCHEMA.TABLE_STORAGE
"""

# Recent failed jobs, with the error reason -> ResourceFailures rule.
JOBS_FAILURES_QUERY = """
SELECT
  job_id, state,
  error_result.reason  AS error_reason,
  error_result.message AS error_message,
  statement_type, query
FROM `{region}`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE error_result IS NOT NULL
  AND creation_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {lookback_days} DAY)
ORDER BY creation_time DESC
LIMIT {limit}
"""
