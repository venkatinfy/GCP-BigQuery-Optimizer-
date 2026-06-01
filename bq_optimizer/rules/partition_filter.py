from typing import List, Set
import sqlglot
import sqlglot.expressions as exp
from .base import BaseRule, Finding, Severity

PARTITION_COLUMN_NAMES: Set[str] = {
    "_partitiontime", "_partitiondate",
    "partition_date", "event_date", "created_at",
    "timestamp", "date", "dt", "event_timestamp",
    "created_date", "updated_at", "load_date",
}


class PartitionFilterRule(BaseRule):
    rule_id = "PARTITION_FILTER"
    title = "Missing partition filter"

    def _has_partition_filter(self, where: exp.Expression) -> bool:
        """Check if the WHERE clause contains a filter on a known partition column."""
        for col in where.find_all(exp.Column):
            col_name = (col.name or "").lower()
            if col_name in PARTITION_COLUMN_NAMES:
                return True
        return False

    def analyze(self, expression: exp.Expression, original_sql: str, context=None) -> List[Finding]:
        findings: List[Finding] = []
        for select in expression.find_all(exp.Select):
            from_clause = select.args.get("from") or select.args.get("from_")
            if not from_clause:
                continue
            where = select.args.get("where") or select.args.get("where_")

            # Check if the query selects from a table that hints at partitioning
            table_refs: List[str] = []
            for table in select.find_all(exp.Table):
                table_refs.append(table.name.lower() if table.name else "")

            # Heuristic: if table name ends in _YYYYMMDD pattern or contains date/event/log
            import re
            date_suffix_pattern = re.compile(r"_\d{8}$|events|logs|sessions|metrics|facts")
            partitioned_table = any(date_suffix_pattern.search(t) for t in table_refs)

            if not partitioned_table:
                # Also check column references in select expressions
                for col in select.find_all(exp.Column):
                    col_name = (col.name or "").lower()
                    if col_name in PARTITION_COLUMN_NAMES:
                        partitioned_table = True
                        break

            if partitioned_table:
                if not where or not self._has_partition_filter(where):
                    table_name = table_refs[0] if table_refs else "the table"
                    findings.append(Finding(
                        rule_id=self.rule_id,
                        title=self.title,
                        severity=Severity.WARNING,
                        description=f"Query on '{table_name}' appears to lack a partition filter, potentially scanning all partitions.",
                        recommendation="Add a WHERE filter on the partition column to limit data scanned.",
                        original_snippet="FROM ... (no partition filter)",
                        suggested_snippet="WHERE _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)",
                    ))
        return findings
