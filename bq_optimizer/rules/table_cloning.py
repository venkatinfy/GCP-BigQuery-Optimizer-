from typing import List
import sqlglot.expressions as exp
from .base import BaseRule, Finding, Severity
from ..util import table_fqn

# Clauses whose presence means the CTAS does real work (not a pure copy).
_TRANSFORM_ARGS = ("where", "group", "having", "joins", "qualify", "distinct",
                   "order", "limit", "offset", "window")


class TableCloningRule(BaseRule):
    rule_id = "TABLE_CLONING"
    title = "CREATE TABLE AS SELECT * should be a clone"

    def _is_pure_copy(self, select: exp.Select) -> bool:
        # Exactly SELECT * with no transformation and a single source table.
        exprs = select.expressions
        if len(exprs) != 1 or not isinstance(exprs[0], exp.Star):
            return False
        if any(select.args.get(arg) for arg in _TRANSFORM_ARGS):
            return False
        tables = list(select.find_all(exp.Table))
        return len(tables) == 1

    def analyze(self, expression: exp.Expression, original_sql: str, context=None) -> List[Finding]:
        findings: List[Finding] = []
        for create in expression.find_all(exp.Create):
            if (create.args.get("kind") or "").upper() != "TABLE":
                continue
            if create.args.get("clone"):
                continue  # already a clone
            select = create.args.get("expression")
            if not isinstance(select, exp.Select) or not self._is_pure_copy(select):
                continue
            target = table_fqn(create.this) if isinstance(create.this, exp.Table) else "new_table"
            source_tbl = next(iter(select.find_all(exp.Table)), None)
            source = table_fqn(source_tbl) if source_tbl else "source"
            findings.append(Finding(
                rule_id=self.rule_id,
                title=self.title,
                severity=Severity.WARNING,
                description=(
                    f"'{target}' is created as a full copy of '{source}' via CREATE TABLE AS "
                    f"SELECT *. CTAS physically rewrites and bills for every byte."
                ),
                recommendation=(
                    "Use a table clone — it is metadata-only, near-instant, and incurs no storage "
                    "cost until the data diverges."
                ),
                original_snippet=f"CREATE TABLE {target} AS SELECT * FROM {source}",
                suggested_snippet=f"CREATE TABLE {target} CLONE {source}",
            ))
        return findings
