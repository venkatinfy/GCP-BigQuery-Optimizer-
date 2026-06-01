from typing import List
import sqlglot.expressions as exp
from .base import BaseRule, Finding, Severity
from ..util import table_fqn


class NativeConversionRule(BaseRule):
    rule_id = "NATIVE_CONVERSION"
    title = "External table used in a join"
    requires_metadata = True

    def analyze(self, expression: exp.Expression, original_sql: str, context=None) -> List[Finding]:
        if context is None or context.metadata is None:
            return []
        findings: List[Finding] = []
        seen: set = set()
        for select in expression.find_all(exp.Select):
            if not (select.args.get("joins")):
                continue  # only flag external tables participating in joins
            for table in select.find_all(exp.Table):
                fqn = table_fqn(table)
                if not fqn or fqn.lower() in seen:
                    continue
                meta = context.metadata.get_table(fqn)
                if meta and meta.is_external:
                    seen.add(fqn.lower())
                    findings.append(Finding(
                        rule_id=self.rule_id,
                        title=self.title,
                        severity=Severity.WARNING,
                        description=(
                            f"'{fqn}' is an EXTERNAL table used in a join. External tables are read "
                            f"on every query with no caching, no clustering, and limited pruning, "
                            f"which is costly inside joins."
                        ),
                        recommendation=(
                            "Load the external data into a native BigQuery table (e.g. via "
                            "CREATE TABLE AS SELECT or a scheduled load) so joins benefit from "
                            "storage optimization, partitioning, clustering, and result caching."
                        ),
                        original_snippet=f"JOIN {fqn}  -- EXTERNAL",
                        suggested_snippet=f"JOIN {fqn}_native  -- materialized native table",
                    ))
        return findings
