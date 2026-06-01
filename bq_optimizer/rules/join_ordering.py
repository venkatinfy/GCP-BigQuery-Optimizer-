from typing import List, Optional, Tuple
import sqlglot.expressions as exp
from .base import BaseRule, Finding, Severity
from ..util import table_fqn


class JoinOrderingRule(BaseRule):
    rule_id = "JOIN_ORDERING"
    title = "Suboptimal join order for table sizes"
    requires_metadata = True

    def _size(self, fqn: str, metadata) -> Optional[int]:
        meta = metadata.get_table(fqn)
        if not meta:
            return None
        if meta.size_bytes is not None:
            return meta.size_bytes
        return meta.row_count

    def _ordered_tables(self, select: exp.Select) -> List[exp.Table]:
        tables: List[exp.Table] = []
        frm = select.args.get("from_") or select.args.get("from")
        if frm and isinstance(frm.this, exp.Table):
            tables.append(frm.this)
        for join in select.args.get("joins") or []:
            if isinstance(join.this, exp.Table):
                tables.append(join.this)
        return tables

    def analyze(self, expression: exp.Expression, original_sql: str, context=None) -> List[Finding]:
        if context is None or context.metadata is None:
            return []
        findings: List[Finding] = []
        for select in expression.find_all(exp.Select):
            tables = self._ordered_tables(select)
            if len(tables) < 2:
                continue
            sized: List[Tuple[str, int]] = []
            for t in tables:
                fqn = table_fqn(t)
                size = self._size(fqn, context.metadata)
                if size is None:
                    sized = []
                    break  # need sizes for all tables to recommend confidently
                sized.append((fqn, size))
            if not sized:
                continue
            current = [name for name, _ in sized]
            # BigQuery best practice: place the largest table first.
            recommended = [name for name, _ in sorted(sized, key=lambda x: x[1], reverse=True)]
            if current == recommended:
                continue
            findings.append(Finding(
                rule_id=self.rule_id,
                title=self.title,
                severity=Severity.INFO,
                description=(
                    "Joined tables are not ordered largest-first. Current order: "
                    f"{' , '.join(current)}. Joining smaller tables onto a large leading table "
                    f"reduces intermediate shuffle volume."
                ),
                recommendation=(
                    "Reorder the joins so the largest table appears first, then progressively "
                    "smaller tables: " + " , ".join(recommended) + ". Verify with EXPLAIN / the "
                    "query plan, as BigQuery's optimizer may already reorder."
                ),
                original_snippet="FROM " + " JOIN ".join(current),
                suggested_snippet="FROM " + " JOIN ".join(recommended),
            ))
        return findings
