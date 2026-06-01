from typing import List
import sqlglot.expressions as exp
from .base import SessionRule, Finding, Severity
from ..util import table_fqn, insert_target


class MergeOptimizationRule(SessionRule):
    rule_id = "MERGE_OPTIMIZATION"
    title = "Separate INSERT and UPDATE should be a MERGE"

    def analyze_session(self, statements: List[exp.Expression], context) -> List[Finding]:
        inserted = {}
        updated = {}
        for stmt in statements:
            if isinstance(stmt, exp.Insert):
                name = insert_target(stmt).lower()
                if name:
                    inserted[name] = insert_target(stmt)
            elif isinstance(stmt, exp.Update):
                tbl = stmt.this if isinstance(stmt.this, exp.Table) else stmt.find(exp.Table)
                if tbl:
                    updated[table_fqn(tbl).lower()] = table_fqn(tbl)

        findings: List[Finding] = []
        for key in sorted(set(inserted) & set(updated)):
            name = inserted[key]
            findings.append(Finding(
                rule_id=self.rule_id,
                title=self.title,
                severity=Severity.WARNING,
                description=(
                    f"The session both INSERTs into and UPDATEs '{name}'. Running these as separate "
                    f"statements scans the target twice and is not atomic."
                ),
                recommendation=(
                    "Combine the insert and update into a single MERGE statement. MERGE performs the "
                    "upsert in one pass, is atomic, and lets BigQuery prune the target once."
                ),
                original_snippet=f"INSERT INTO {name} ...; UPDATE {name} SET ...;",
                suggested_snippet=(
                    f"MERGE {name} T USING source S ON T.id = S.id "
                    f"WHEN MATCHED THEN UPDATE SET ... WHEN NOT MATCHED THEN INSERT ..."
                ),
            ))
        return findings
