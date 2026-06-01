from collections import Counter
from typing import List
import sqlglot.expressions as exp
from .base import BaseRule, Finding, Severity
from ..util import physical_tables, table_fqn


class RedundantScansRule(BaseRule):
    rule_id = "REDUNDANT_SCANS"
    title = "Same table scanned multiple times in one statement"

    def analyze(self, expression: exp.Expression, original_sql: str, context=None) -> List[Finding]:
        findings: List[Finding] = []
        counts = Counter(table_fqn(t).lower() for t in physical_tables(expression) if table_fqn(t))
        for name, count in counts.items():
            if count >= 2:
                findings.append(Finding(
                    rule_id=self.rule_id,
                    title=self.title,
                    severity=Severity.WARNING,
                    description=(
                        f"Table '{name}' is referenced {count} times in a single statement, "
                        f"causing it to be scanned repeatedly."
                    ),
                    recommendation=(
                        "Scan the table once into a CTE (WITH clause) or temporary table and reuse it, "
                        "or collapse the logic using window functions / conditional aggregation. "
                        "If this is an intentional self-join, confirm both scans are required."
                    ),
                    original_snippet=f"... FROM {name} ... JOIN {name} ...",
                    suggested_snippet=f"WITH src AS (SELECT ... FROM {name}) SELECT ... FROM src ...",
                ))
        return findings
