from typing import List
import sqlglot
import sqlglot.expressions as exp
from .base import BaseRule, Finding, Severity


class CountDistinctRule(BaseRule):
    rule_id = "COUNT_DISTINCT"
    title = "COUNT(DISTINCT ...) usage"

    def analyze(self, expression: exp.Expression, original_sql: str, context=None) -> List[Finding]:
        findings: List[Finding] = []
        for func in expression.find_all(exp.Count):
            # sqlglot represents COUNT(DISTINCT x) as Count(this=Distinct(expressions=[col]))
            inner = func.this
            if isinstance(inner, exp.Distinct):
                exprs = inner.expressions
                col_sql = exprs[0].sql(dialect="bigquery") if exprs else "col"
            elif func.args.get("distinct"):
                col_expr = inner
                col_sql = col_expr.sql(dialect="bigquery") if col_expr else "col"
            else:
                continue
            findings.append(Finding(
                rule_id=self.rule_id,
                title=self.title,
                severity=Severity.INFO,
                description=f"COUNT(DISTINCT {col_sql}) performs an exact count which can be expensive on large tables.",
                recommendation="Consider APPROX_COUNT_DISTINCT(col) for large tables — it runs faster with ~1% error margin.",
                original_snippet=f"COUNT(DISTINCT {col_sql})",
                suggested_snippet=f"APPROX_COUNT_DISTINCT({col_sql})",
            ))
        return findings
