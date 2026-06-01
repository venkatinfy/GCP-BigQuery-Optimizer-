from typing import List, Optional
import sqlglot.expressions as exp
from .base import BaseRule, Finding, Severity
from ..util import table_fqn


class UnfilteredPartitionRule(BaseRule):
    rule_id = "UNFILTERED_PARTITION"
    title = "EXCEPT DISTINCT without a partition filter"

    def _partition_column(self, select: exp.Select, context) -> Optional[str]:
        if context is None or context.metadata is None:
            return None
        for table in select.find_all(exp.Table):
            meta = context.metadata.get_table(table_fqn(table))
            if meta and meta.partition_column:
                return meta.partition_column
        return None

    def _filters_on(self, select: exp.Select, column: Optional[str]) -> bool:
        where = select.args.get("where")
        if where is None:
            return False
        if column is None:
            return True  # has some filter; cannot prove it is the partition column
        target = column.lower()
        return any((c.name or "").lower() == target for c in where.find_all(exp.Column))

    def _branch_unfiltered(self, branch: exp.Expression, context) -> bool:
        if not isinstance(branch, exp.Select):
            return False
        partition_col = self._partition_column(branch, context)
        if context is not None and context.metadata is not None:
            # Only flag tables we *know* are partitioned.
            if partition_col is None:
                return False
            return not self._filters_on(branch, partition_col)
        # No metadata: advisory only when a branch has no WHERE at all.
        return branch.args.get("where") is None

    def analyze(self, expression: exp.Expression, original_sql: str, context=None) -> List[Finding]:
        findings: List[Finding] = []
        for op in expression.find_all(exp.Except):
            if not op.args.get("distinct"):
                continue
            branches = [op.this, op.expression]
            if any(self._branch_unfiltered(b, context) for b in branches):
                findings.append(Finding(
                    rule_id=self.rule_id,
                    title=self.title,
                    severity=Severity.WARNING,
                    description=(
                        "An EXCEPT DISTINCT compares full rows across its inputs with at least one "
                        "side lacking a partition filter, forcing a scan of every partition before "
                        "the set difference is computed."
                    ),
                    recommendation=(
                        "Add a WHERE filter on the partition column to each side of the "
                        "EXCEPT DISTINCT so only the relevant partitions are scanned, and select "
                        "only the columns you need rather than all of them."
                    ),
                    original_snippet="SELECT * FROM t EXCEPT DISTINCT SELECT * FROM s",
                    suggested_snippet=(
                        "SELECT * FROM t WHERE part_col >= @start "
                        "EXCEPT DISTINCT SELECT * FROM s WHERE part_col >= @start"
                    ),
                ))
        return findings
