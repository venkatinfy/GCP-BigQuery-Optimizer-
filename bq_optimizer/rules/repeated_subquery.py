from typing import List
import sqlglot
import sqlglot.expressions as exp
from .base import BaseRule, Finding, Severity


class RepeatedSubqueryRule(BaseRule):
    rule_id = "REPEATED_SUBQUERY"
    title = "Repeated subquery detected"

    def analyze(self, expression: exp.Expression, original_sql: str) -> List[Finding]:
        findings: List[Finding] = []
        subquery_texts: List[str] = []
        seen: set = set()
        duplicates: set = set()

        for subquery in expression.find_all(exp.Subquery):
            sql_text = subquery.this.sql(dialect="bigquery").strip()
            if sql_text in seen:
                duplicates.add(sql_text)
            else:
                seen.add(sql_text)

        for dup in duplicates:
            short = dup[:80] + ("..." if len(dup) > 80 else "")
            findings.append(Finding(
                rule_id=self.rule_id,
                title=self.title,
                severity=Severity.WARNING,
                description=f"Subquery appears more than once: {short}",
                recommendation="Extract repeated subquery into a CTE (WITH clause) to avoid redundant computation.",
                original_snippet=short,
                suggested_snippet="WITH cte AS (" + short + ") SELECT ... FROM cte",
            ))
        return findings
