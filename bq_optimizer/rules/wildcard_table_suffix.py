"""WILDCARD_TABLE_SUFFIX rule.

Detects use of the _TABLE_SUFFIX pseudo-column in WHERE clauses, which indicates
the query is scanning wildcard tables (e.g. `project.dataset.events_*`).
Wildcard table scans still enumerate all matching shards; partitioned tables
offer better pruning, cheaper metadata access, and simpler syntax.
"""
from typing import List
import sqlglot.expressions as exp
from .base import BaseRule, Finding, Severity


class WildcardTableSuffixRule(BaseRule):
    rule_id = "WILDCARD_TABLE_SUFFIX"
    title = "Wildcard table (_TABLE_SUFFIX) usage detected"

    def analyze(self, expression: exp.Expression, original_sql: str, context=None) -> List[Finding]:
        findings: List[Finding] = []
        # Look for _TABLE_SUFFIX column references
        for col in expression.find_all(exp.Column):
            if (col.name or "").upper() == "_TABLE_SUFFIX":
                col_sql = col.sql(dialect="bigquery")
                findings.append(Finding(
                    rule_id=self.rule_id,
                    title=self.title,
                    severity=Severity.INFO,
                    description=(
                        "_TABLE_SUFFIX is a pseudo-column used with wildcard table queries "
                        "(e.g. FROM `project.dataset.events_*`). Wildcard scans enumerate "
                        "every matching shard table, leading to higher metadata costs and "
                        "less efficient pruning than partitioned tables."
                    ),
                    recommendation=(
                        "Consider migrating date-sharded tables to a single partitioned "
                        "table. Use PARTITION BY DATE(event_timestamp) and filter with "
                        "WHERE DATE(event_timestamp) BETWEEN date1 AND date2."
                    ),
                    original_snippet=col_sql,
                    suggested_snippet="WHERE DATE(event_timestamp) BETWEEN '2023-01-01' AND '2023-12-31'",
                ))
                break  # one finding per query is enough
        return findings
