from typing import List
import sqlglot
import sqlglot.expressions as exp
from .base import BaseRule, Finding, Severity


class ScalarSubqueryInSelectRule(BaseRule):
    rule_id = "SCALAR_SUBQUERY_IN_SELECT"
    title = "Scalar subquery in SELECT list"

    def analyze(self, expression: exp.Expression, original_sql: str, context=None) -> List[Finding]:
        findings: List[Finding] = []
        for select in expression.find_all(exp.Select):
            for item in select.expressions:
                # Look for subqueries directly in select expressions
                for subquery in item.find_all(exp.Subquery):
                    sql_text = subquery.sql(dialect="bigquery")
                    short = sql_text[:80] + ("..." if len(sql_text) > 80 else "")
                    findings.append(Finding(
                        rule_id=self.rule_id,
                        title=self.title,
                        severity=Severity.CRITICAL,
                        description="Correlated scalar subquery in SELECT list executes once per row (N+1 problem).",
                        recommendation="Rewrite correlated scalar subqueries as JOINs or window functions to avoid N+1 execution.",
                        original_snippet=short,
                        suggested_snippet="LEFT JOIN subquery_table ON ... (or window function)",
                    ))
                    break  # one finding per select item
        return findings
