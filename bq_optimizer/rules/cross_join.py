from typing import List
import sqlglot
import sqlglot.expressions as exp
from .base import BaseRule, Finding, Severity


class CrossJoinRule(BaseRule):
    rule_id = "CROSS_JOIN"
    title = "CROSS JOIN detected"

    def analyze(self, expression: exp.Expression, original_sql: str) -> List[Finding]:
        findings: List[Finding] = []
        for join in expression.find_all(exp.Join):
            kind = join.args.get("kind")
            is_cross = (
                join.args.get("cross")
                or (isinstance(kind, str) and kind.upper() == "CROSS")
                or (hasattr(kind, "name") and kind.name.upper() == "CROSS")  # type: ignore[union-attr]
            )
            if is_cross:
                table_name = ""
                if join.this:
                    table_name = join.this.sql(dialect="bigquery")
                findings.append(Finding(
                    rule_id=self.rule_id,
                    title=self.title,
                    severity=Severity.CRITICAL,
                    description=f"CROSS JOIN with {table_name} produces a cartesian product of all rows.",
                    recommendation="Replace with INNER JOIN / LEFT JOIN with an ON condition, or confirm intentional cartesian product.",
                    original_snippet=f"CROSS JOIN {table_name}",
                    suggested_snippet=f"INNER JOIN {table_name} ON ...",
                ))
        return findings
