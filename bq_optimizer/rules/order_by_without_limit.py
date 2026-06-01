from typing import List
import sqlglot
import sqlglot.expressions as exp
from .base import BaseRule, Finding, Severity


class OrderByWithoutLimitRule(BaseRule):
    rule_id = "ORDER_BY_WITHOUT_LIMIT"
    title = "ORDER BY without LIMIT"

    def analyze(self, expression: exp.Expression, original_sql: str, context=None) -> List[Finding]:
        findings: List[Finding] = []
        # Check top-level select
        if isinstance(expression, exp.Select):
            selects = [expression]
        else:
            selects = list(expression.find_all(exp.Select))

        for select in selects:
            order = select.args.get("order")
            limit = select.args.get("limit")
            if order and not limit:
                order_sql = order.sql(dialect="bigquery")
                findings.append(Finding(
                    rule_id=self.rule_id,
                    title=self.title,
                    severity=Severity.WARNING,
                    description="ORDER BY without LIMIT forces a full sort of all result rows, wasting slot time.",
                    recommendation="Remove ORDER BY or add LIMIT — sorting a full scan wastes slot time.",
                    original_snippet=order_sql,
                    suggested_snippet=f"{order_sql} LIMIT 1000",
                ))
        return findings
