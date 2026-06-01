from typing import List
import sqlglot.expressions as exp
from .base import BaseRule, Finding, Severity


class LargeInClauseRule(BaseRule):
    rule_id = "LARGE_IN_CLAUSE"
    title = "Excessive values in IN clause"

    THRESHOLD = 50

    def analyze(self, expression: exp.Expression, original_sql: str, context=None) -> List[Finding]:
        findings: List[Finding] = []
        for in_node in expression.find_all(exp.In):
            values = in_node.expressions  # literal list; empty for IN (subquery)
            if not values or len(values) < self.THRESHOLD:
                continue
            col = in_node.this.sql(dialect="bigquery") if in_node.this else "col"
            findings.append(Finding(
                rule_id=self.rule_id,
                title=self.title,
                severity=Severity.WARNING,
                description=(
                    f"IN list on '{col}' contains {len(values)} values. Very large inline lists "
                    f"inflate the query text, slow planning, and cannot be pruned efficiently."
                ),
                recommendation=(
                    "Load the values into a temporary/staging table (or UNNEST an array parameter) "
                    "and JOIN against it, letting BigQuery use a hash join and partition pruning."
                ),
                original_snippet=f"{col} IN (v1, v2, ... v{len(values)})",
                suggested_snippet=f"JOIN tmp_values t ON t.value = {col}",
            ))
        return findings
