from typing import List
import sqlglot.expressions as exp
from .base import BaseRule, Finding, Severity


class StringComparisonRule(BaseRule):
    rule_id = "STRING_COMPARISON"
    title = "UPPER()/LOWER() used for case-insensitive comparison"

    def analyze(self, expression: exp.Expression, original_sql: str, context=None) -> List[Finding]:
        findings: List[Finding] = []
        seen: set = set()
        for fn in expression.find_all(exp.Upper, exp.Lower):
            if not isinstance(fn.this, exp.Column):
                continue
            # Only care when the call sits inside a filter/join predicate.
            if not fn.find_ancestor(exp.Where, exp.Join, exp.Having, exp.Qualify):
                continue
            col = fn.this.sql(dialect="bigquery")
            func = type(fn).__name__.upper()
            key = (func, col)
            if key in seen:
                continue
            seen.add(key)
            findings.append(Finding(
                rule_id=self.rule_id,
                title=self.title,
                severity=Severity.INFO,
                description=(
                    f"{func}({col}) wraps a column inside a predicate to force case-insensitive "
                    f"matching. Wrapping the column in a function makes the predicate non-sargable "
                    f"(no partition/cluster pruning) and runs per row."
                ),
                recommendation=(
                    "Define the column with a case-insensitive collation (e.g. COLLATE 'und:ci') so "
                    "comparisons are case-insensitive without a function, or store a normalized column "
                    "once and compare against it. Avoid wrapping the column side of the predicate."
                ),
                original_snippet=f"{func}({col}) = {func}('value')",
                suggested_snippet=f"{col} = 'value'  -- with column COLLATE 'und:ci'",
            ))
        return findings
