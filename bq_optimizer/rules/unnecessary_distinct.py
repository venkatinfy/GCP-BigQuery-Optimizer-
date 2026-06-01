from typing import List
import sqlglot
import sqlglot.expressions as exp
from .base import BaseRule, Finding, Severity


class UnnecessaryDistinctRule(BaseRule):
    rule_id = "UNNECESSARY_DISTINCT"
    title = "Unnecessary DISTINCT with GROUP BY"

    def analyze(self, expression: exp.Expression, original_sql: str, context=None) -> List[Finding]:
        findings: List[Finding] = []
        for select in expression.find_all(exp.Select):
            has_distinct = select.args.get("distinct")
            has_group_by = select.args.get("group")
            if has_distinct and has_group_by:
                findings.append(Finding(
                    rule_id=self.rule_id,
                    title=self.title,
                    severity=Severity.INFO,
                    description="SELECT DISTINCT combined with GROUP BY is redundant — GROUP BY already produces unique rows.",
                    recommendation="Remove DISTINCT — GROUP BY already produces unique rows.",
                    original_snippet="SELECT DISTINCT ... GROUP BY ...",
                    suggested_snippet="SELECT ... GROUP BY ...",
                ))
        return findings
