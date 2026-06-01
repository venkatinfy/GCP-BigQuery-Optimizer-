"""DATETIME_TRUNC_CAST rule.

Detects CAST(col AS DATE) used in WHERE filters on partition columns.
In BigQuery, wrapping a partition column with CAST() prevents partition pruning.
Use DATE(col) or DATE_TRUNC(col, DAY) instead, which are partition-safe.
"""
from typing import List
import re
import sqlglot.expressions as exp
from .base import BaseRule, Finding, Severity

PARTITION_COLUMN_NAMES = {
    "_partitiontime", "_partitiondate",
    "partition_date", "event_date", "created_at",
    "timestamp", "date", "dt", "event_timestamp",
    "created_date", "updated_at", "load_date",
}


class DatetimeTruncCastRule(BaseRule):
    rule_id = "DATETIME_TRUNC_CAST"
    title = "CAST() on partition column prevents partition pruning"

    def _is_partition_col(self, node: exp.Expression) -> bool:
        if isinstance(node, exp.Column):
            return (node.name or "").lower() in PARTITION_COLUMN_NAMES
        return False

    def analyze(self, expression: exp.Expression, original_sql: str, context=None) -> List[Finding]:
        findings: List[Finding] = []
        for cast in expression.find_all(exp.Cast):
            # Check if the cast is wrapping a known partition column
            inner = cast.this
            if not self._is_partition_col(inner):
                continue
            # Check if the cast is used inside a WHERE / predicate context
            # Walk up the AST to see if there is a Where ancestor
            parent = cast.parent
            in_where = False
            while parent is not None:
                if isinstance(parent, exp.Where):
                    in_where = True
                    break
                parent = parent.parent
            if not in_where:
                continue
            col_sql = inner.sql(dialect="bigquery")
            cast_sql = cast.sql(dialect="bigquery")
            findings.append(Finding(
                rule_id=self.rule_id,
                title=self.title,
                severity=Severity.WARNING,
                description=(
                    f"CAST({col_sql} AS DATE) in a WHERE clause prevents BigQuery from pruning "
                    "partitions, causing a full table scan."
                ),
                recommendation=(
                    f"Replace CAST({col_sql} AS DATE) with DATE({col_sql}) or use "
                    f"DATE_TRUNC({col_sql}, DAY) to preserve partition pruning."
                ),
                original_snippet=cast_sql,
                suggested_snippet=f"DATE({col_sql})",
            ))
        return findings
