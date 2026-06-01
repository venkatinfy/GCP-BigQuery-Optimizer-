from typing import List
import sqlglot
import sqlglot.expressions as exp
from .base import BaseRule, Finding, Severity


class LikeLeadingWildcardRule(BaseRule):
    rule_id = "LIKE_LEADING_WILDCARD"
    title = "LIKE with leading wildcard"

    def analyze(self, expression: exp.Expression, original_sql: str) -> List[Finding]:
        findings: List[Finding] = []
        for like in expression.find_all(exp.Like):
            pattern_expr = like.args.get("expression") or like.right
            if pattern_expr is None:
                continue
            pattern = ""
            if isinstance(pattern_expr, exp.Literal):
                pattern = pattern_expr.this or ""
            if pattern.startswith("%"):
                col_sql = like.this.sql(dialect="bigquery") if like.this else "col"
                findings.append(Finding(
                    rule_id=self.rule_id,
                    title=self.title,
                    severity=Severity.INFO,
                    description=f"LIKE '{pattern}' uses a leading wildcard which prevents filter pushdown.",
                    recommendation="Leading-wildcard LIKE prevents index/filter pushdown. Consider REGEXP_CONTAINS or restructuring the filter.",
                    original_snippet=f"{col_sql} LIKE '{pattern}'",
                    suggested_snippet=f"REGEXP_CONTAINS({col_sql}, r'{pattern.strip('%')}')",
                ))
        return findings
