from typing import List
import sqlglot
import sqlglot.expressions as exp
from .base import BaseRule, Finding, Severity


class SelectStarRule(BaseRule):
    rule_id = "SELECT_STAR"
    title = "SELECT * usage detected"

    def analyze(self, expression: exp.Expression, original_sql: str, context=None) -> List[Finding]:
        findings: List[Finding] = []
        for select in expression.find_all(exp.Select):
            for col in select.expressions:
                if isinstance(col, exp.Star):
                    findings.append(Finding(
                        rule_id=self.rule_id,
                        title=self.title,
                        severity=Severity.WARNING,
                        description="SELECT * retrieves all columns, increasing bytes scanned and cost.",
                        recommendation="Explicitly list only required columns to reduce bytes scanned and improve partition/cluster pruning.",
                        original_snippet="SELECT *",
                        suggested_snippet="SELECT col1, col2, ...",
                    ))
                    break
                elif isinstance(col, exp.Column) and isinstance(col.this, exp.Star):
                    alias = col.table or "t"
                    findings.append(Finding(
                        rule_id=self.rule_id,
                        title=self.title,
                        severity=Severity.WARNING,
                        description=f"SELECT {alias}.* retrieves all columns from {alias}, increasing bytes scanned.",
                        recommendation="Explicitly list only required columns to reduce bytes scanned and improve partition/cluster pruning.",
                        original_snippet=f"SELECT {alias}.*",
                        suggested_snippet=f"SELECT {alias}.col1, {alias}.col2, ...",
                    ))
                    break
        return findings
