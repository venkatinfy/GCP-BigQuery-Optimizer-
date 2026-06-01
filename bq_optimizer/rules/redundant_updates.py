from collections import Counter
from typing import List
import sqlglot.expressions as exp
from .base import SessionRule, Finding, Severity
from ..util import table_fqn


class RedundantUpdatesRule(SessionRule):
    rule_id = "REDUNDANT_UPDATES"
    title = "Same table updated multiple times"

    def analyze_session(self, statements: List[exp.Expression], context) -> List[Finding]:
        counts: Counter = Counter()
        display = {}
        for stmt in statements:
            if isinstance(stmt, exp.Update):
                tbl = stmt.this if isinstance(stmt.this, exp.Table) else stmt.find(exp.Table)
                if tbl:
                    name = table_fqn(tbl)
                    counts[name.lower()] += 1
                    display[name.lower()] = name

        findings: List[Finding] = []
        for key, count in counts.items():
            if count >= 2:
                name = display[key]
                findings.append(Finding(
                    rule_id=self.rule_id,
                    title=self.title,
                    severity=Severity.WARNING,
                    description=(
                        f"'{name}' is updated {count} times in the same execution. Each UPDATE "
                        f"rewrites the affected storage blocks and is billed separately."
                    ),
                    recommendation=(
                        "Consolidate the updates into a single UPDATE (combine the SET expressions "
                        "with CASE) or a single MERGE so the table is rewritten only once."
                    ),
                    original_snippet=f"UPDATE {name} SET a=...; UPDATE {name} SET b=...;",
                    suggested_snippet=f"UPDATE {name} SET a=..., b=... WHERE ...;",
                ))
        return findings
