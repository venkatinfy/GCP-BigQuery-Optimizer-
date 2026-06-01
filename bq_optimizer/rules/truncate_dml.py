from typing import List
import sqlglot.expressions as exp
from .base import BaseRule, Finding, Severity
from ..util import table_fqn


def _is_trivially_true(where: exp.Expression) -> bool:
    """True for predicates like WHERE TRUE or WHERE 1 = 1."""
    cond = where.this if isinstance(where, exp.Where) else where
    if isinstance(cond, exp.Boolean) and cond.this is True:
        return True
    if isinstance(cond, exp.EQ):
        left, right = cond.left, cond.right
        if (isinstance(left, exp.Literal) and isinstance(right, exp.Literal)
                and left.name == right.name):
            return True
    return False


class TruncateDmlRule(BaseRule):
    rule_id = "TRUNCATE_DML"
    title = "Full-table DELETE should be TRUNCATE"

    def analyze(self, expression: exp.Expression, original_sql: str, context=None) -> List[Finding]:
        findings: List[Finding] = []
        for delete in expression.find_all(exp.Delete):
            where = delete.args.get("where")
            if where is not None and not _is_trivially_true(where):
                continue
            table = delete.this.find(exp.Table) if delete.this else None
            name = table_fqn(table) if table else "the table"
            findings.append(Finding(
                rule_id=self.rule_id,
                title=self.title,
                severity=Severity.WARNING,
                description=(
                    f"DELETE on '{name}' has no selective WHERE clause, so every row is removed. "
                    f"Unbounded DELETE is billed for bytes processed and generates change history."
                ),
                recommendation=(
                    "Use TRUNCATE TABLE for a full wipe — it is free, atomic, and far faster than "
                    "a row-by-row DELETE."
                ),
                original_snippet=f"DELETE FROM {name}",
                suggested_snippet=f"TRUNCATE TABLE {name}",
            ))
        return findings
