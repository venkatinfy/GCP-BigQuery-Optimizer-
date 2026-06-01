from typing import List
import sqlglot
import sqlglot.expressions as exp
from .base import BaseRule, Finding, Severity


class NullComparisonRule(BaseRule):
    rule_id = "NULL_COMPARISON"
    title = "Incorrect NULL comparison"

    def analyze(self, expression: exp.Expression, original_sql: str, context=None) -> List[Finding]:
        findings: List[Finding] = []
        for eq in expression.find_all(exp.EQ):
            left, right = eq.left, eq.right
            if isinstance(right, exp.Null):
                col_sql = left.sql(dialect="bigquery")
                findings.append(Finding(
                    rule_id=self.rule_id,
                    title=self.title,
                    severity=Severity.CRITICAL,
                    description=f"'{col_sql} = NULL' always evaluates to NULL, never TRUE.",
                    recommendation="Use IS NULL / IS NOT NULL — equality comparisons with NULL always return NULL (never TRUE).",
                    original_snippet=f"{col_sql} = NULL",
                    suggested_snippet=f"{col_sql} IS NULL",
                ))
            elif isinstance(left, exp.Null):
                col_sql = right.sql(dialect="bigquery")
                findings.append(Finding(
                    rule_id=self.rule_id,
                    title=self.title,
                    severity=Severity.CRITICAL,
                    description=f"'NULL = {col_sql}' always evaluates to NULL, never TRUE.",
                    recommendation="Use IS NULL / IS NOT NULL — equality comparisons with NULL always return NULL (never TRUE).",
                    original_snippet=f"NULL = {col_sql}",
                    suggested_snippet=f"{col_sql} IS NULL",
                ))

        for neq in expression.find_all(exp.NEQ):
            left, right = neq.left, neq.right
            if isinstance(right, exp.Null):
                col_sql = left.sql(dialect="bigquery")
                findings.append(Finding(
                    rule_id=self.rule_id,
                    title=self.title,
                    severity=Severity.CRITICAL,
                    description=f"'{col_sql} != NULL' always evaluates to NULL, never TRUE.",
                    recommendation="Use IS NULL / IS NOT NULL — equality comparisons with NULL always return NULL (never TRUE).",
                    original_snippet=f"{col_sql} != NULL",
                    suggested_snippet=f"{col_sql} IS NOT NULL",
                ))
            elif isinstance(left, exp.Null):
                col_sql = right.sql(dialect="bigquery")
                findings.append(Finding(
                    rule_id=self.rule_id,
                    title=self.title,
                    severity=Severity.CRITICAL,
                    description=f"'NULL != {col_sql}' always evaluates to NULL, never TRUE.",
                    recommendation="Use IS NULL / IS NOT NULL — equality comparisons with NULL always return NULL (never TRUE).",
                    original_snippet=f"NULL != {col_sql}",
                    suggested_snippet=f"{col_sql} IS NOT NULL",
                ))
        return findings
