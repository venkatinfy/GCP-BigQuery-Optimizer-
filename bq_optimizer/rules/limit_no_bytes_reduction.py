from typing import List
import sqlglot.expressions as exp
from .base import BaseRule, Finding, Severity


class LimitNoBytesReductionRule(BaseRule):
    rule_id = "LIMIT_NO_BYTES_REDUCTION"
    title = "LIMIT does not reduce bytes scanned"

    def analyze(self, expression: exp.Expression, original_sql: str, context=None) -> List[Finding]:
        findings: List[Finding] = []
        for select in expression.find_all(exp.Select):
            limit = select.args.get("limit")
            if not limit:
                continue
            where = select.args.get("where") or select.args.get("where_")
            if where:
                continue
            # Only flag selects that have a FROM clause (not e.g. SELECT 1)
            from_clause = select.args.get("from") or select.args.get("from_")
            if not from_clause:
                continue
            limit_sql = limit.sql(dialect="bigquery")
            findings.append(Finding(
                rule_id=self.rule_id,
                title=self.title,
                severity=Severity.INFO,
                description=(
                    "LIMIT restricts the number of rows returned but does NOT reduce bytes "
                    "scanned in BigQuery. Without a WHERE/partition filter, BigQuery scans "
                    "the entire table before applying LIMIT."
                ),
                recommendation=(
                    "Add a WHERE clause (ideally on a partition column) to reduce bytes scanned. "
                    "LIMIT alone has no cost benefit in BigQuery."
                ),
                original_snippet=limit_sql,
                suggested_snippet="WHERE _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)",
            ))
        return findings
