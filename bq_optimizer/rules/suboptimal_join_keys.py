from typing import List, Optional
import sqlglot.expressions as exp
from .base import BaseRule, Finding, Severity
from ..util import build_alias_map


class SuboptimalJoinKeysRule(BaseRule):
    rule_id = "SUBOPTIMAL_JOIN_KEYS"
    title = "STRING column used as a join key"
    requires_metadata = True

    def _resolve_type(self, column: exp.Column, alias_map, metadata) -> Optional[str]:
        qualifier = (column.table or "").lower()
        fqn = alias_map.get(qualifier)
        if fqn is None and len(set(alias_map.values())) == 1:
            fqn = next(iter(alias_map.values()))
        if not fqn:
            return None
        table = metadata.get_table(fqn)
        if not table:
            return None
        col = table.column(column.name)
        return col.data_type if col else None

    def analyze(self, expression: exp.Expression, original_sql: str, context=None) -> List[Finding]:
        if context is None or context.metadata is None:
            return []
        findings: List[Finding] = []
        seen: set = set()
        for select in expression.find_all(exp.Select):
            alias_map = build_alias_map(select)
            for join in select.args.get("joins") or []:
                on = join.args.get("on")
                if on is None:
                    continue
                for eq in on.find_all(exp.EQ):
                    for side in (eq.left, eq.right):
                        if not isinstance(side, exp.Column):
                            continue
                        data_type = self._resolve_type(side, alias_map, context.metadata)
                        if data_type and data_type.upper() in {"STRING", "BYTES"}:
                            label = side.sql(dialect="bigquery")
                            if label in seen:
                                continue
                            seen.add(label)
                            findings.append(Finding(
                                rule_id=self.rule_id,
                                title=self.title,
                                severity=Severity.INFO,
                                description=(
                                    f"Join key '{label}' is typed {data_type}. STRING joins hash and "
                                    f"compare far more bytes than integer keys, increasing shuffle and "
                                    f"slot time on large joins."
                                ),
                                recommendation=(
                                    "Prefer INT64 surrogate keys for join columns. Where strings are "
                                    "unavoidable, ensure both sides share an identical collation and "
                                    "consider clustering on the key."
                                ),
                                original_snippet=f"ON ... {label} (STRING) ...",
                                suggested_snippet=f"ON ... {label} (INT64 surrogate key) ...",
                            ))
        return findings
