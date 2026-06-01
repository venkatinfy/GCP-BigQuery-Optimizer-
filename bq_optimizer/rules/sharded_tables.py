"""SHARDED_TABLES rule.

Date-sharded tables (tablename_YYYYMMDD) are a legacy BigQuery anti-pattern.
Each shard is a separate table, so:
- Metadata operations are slow (schema changes require touching every shard).
- Cross-shard queries using wildcard syntax still scan all matching tables.
- Partitioned tables offer better performance, lower cost, and simpler management.
"""
from typing import List
import re
import sqlglot.expressions as exp
from .base import BaseRule, Finding, Severity

# Match table names ending in an 8-digit date suffix, e.g. events_20230101
_DATE_SHARDED_RE = re.compile(r"_\d{8}$")
# Match wildcard shard queries, e.g. `project.dataset.events_*`
_WILDCARD_SHARD_RE = re.compile(r"_\*$")


class ShardedTablesRule(BaseRule):
    rule_id = "SHARDED_TABLES"
    title = "Date-sharded tables are a legacy anti-pattern"

    def analyze(self, expression: exp.Expression, original_sql: str, context=None) -> List[Finding]:
        findings: List[Finding] = []
        seen: set = set()
        for table in expression.find_all(exp.Table):
            name = table.name or ""
            # Also check db.table notation
            full = ".".join(
                p for p in [
                    table.args.get("catalog") and table.args["catalog"].name,
                    table.args.get("db") and table.args["db"].name,
                    name,
                ] if p
            )
            if _DATE_SHARDED_RE.search(name) or _WILDCARD_SHARD_RE.search(name):
                key = full or name
                if key in seen:
                    continue
                seen.add(key)
                display = f"`{full}`" if full else f"`{name}`"
                findings.append(Finding(
                    rule_id=self.rule_id,
                    title=self.title,
                    severity=Severity.WARNING,
                    description=(
                        f"Table {display} appears to be a date-sharded table. "
                        "Date-sharded tables are a legacy BigQuery pattern that leads to "
                        "higher metadata overhead, slower schema changes, and often more "
                        "bytes scanned than equivalent partitioned tables."
                    ),
                    recommendation=(
                        "Migrate to a partitioned table (DATE or TIMESTAMP partition). "
                        "Use CREATE TABLE ... PARTITION BY DATE(event_timestamp) and load "
                        "data into a single table instead of one table per day."
                    ),
                    original_snippet=full or name,
                    suggested_snippet=(
                        "CREATE TABLE project.dataset.events\n"
                        "  PARTITION BY DATE(event_timestamp)\n"
                        "OPTIONS (require_partition_filter = true);"
                    ),
                ))
        return findings
