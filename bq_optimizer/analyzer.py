from dataclasses import dataclass, field
from typing import List, Optional
import re
import sqlglot
import sqlglot.expressions as exp

from .rules import STATEMENT_RULES, SESSION_RULES, Finding, Severity
from .context import AnalysisContext
from .metadata.base import MetadataProvider


@dataclass
class AnalysisResult:
    original_sql: str
    findings: List[Finding] = field(default_factory=list)
    rewritten_sql: str = ""
    parse_error: Optional[str] = None
    statement_count: int = 0
    metadata_used: bool = False

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.INFO)

    @property
    def total_count(self) -> int:
        return len(self.findings)


def _apply_rewrites(sql: str, findings: List[Finding]) -> str:
    """Apply safe textual rewrites and suggestion comments to the SQL."""
    result = sql

    # Fix NULL comparisons: col = NULL -> col IS NULL
    result = re.sub(r'(\w+)\s*=\s*NULL\b', r'\1 IS NULL', result, flags=re.IGNORECASE)
    result = re.sub(r'(\w+)\s*!=\s*NULL\b', r'\1 IS NOT NULL', result, flags=re.IGNORECASE)
    result = re.sub(r'(\w+)\s*<>\s*NULL\b', r'\1 IS NOT NULL', result, flags=re.IGNORECASE)

    # Remove DISTINCT when GROUP BY present (simple regex-based approach)
    if re.search(r'\bGROUP\s+BY\b', result, re.IGNORECASE):
        result = re.sub(r'\bSELECT\s+DISTINCT\b', 'SELECT', result, flags=re.IGNORECASE)

    # Add LIMIT suggestion after ORDER BY if no LIMIT
    has_order_by = bool(re.search(r'\bORDER\s+BY\b', result, re.IGNORECASE))
    has_limit = bool(re.search(r'\bLIMIT\s+\d+', result, re.IGNORECASE))
    if has_order_by and not has_limit:
        result = re.sub(
            r'(\bORDER\s+BY\b[^;]*?)(\s*;?\s*$)',
            r'\1 -- SUGGESTION: add LIMIT\2',
            result,
            flags=re.IGNORECASE | re.DOTALL,
        )

    # Per-rule inline suggestion comments keyed off the findings produced.
    rule_ids = {f.rule_id for f in findings}

    if "PARTITION_FILTER" in rule_ids:
        result = re.sub(
            r'(\bFROM\b\s+`?[\w.]+`?)',
            r'\1 -- SUGGESTION: add partition filter in WHERE clause',
            result, count=1, flags=re.IGNORECASE,
        )

    if "TRUNCATE_DML" in rule_ids:
        result = re.sub(
            r'\bDELETE\s+FROM\b',
            'TRUNCATE TABLE /* was: DELETE FROM (no WHERE) */',
            result, count=1, flags=re.IGNORECASE,
        )

    if "TABLE_CLONING" in rule_ids:
        result = re.sub(
            r'(\bCREATE\s+TABLE\b[^;]*?)\bAS\s+SELECT\s+\*\s+FROM\b',
            r'\1CLONE /* was: AS SELECT * FROM */',
            result, count=1, flags=re.IGNORECASE,
        )

    def replace_count_distinct(m: re.Match) -> str:
        inner = m.group(1)
        return f"COUNT(DISTINCT {inner}) /* SUGGESTION: APPROX_COUNT_DISTINCT({inner}) */"

    result = re.sub(
        r'\bCOUNT\s*\(\s*DISTINCT\s+([^)]+)\)',
        replace_count_distinct, result, flags=re.IGNORECASE,
    )

    return result


class QueryAnalyzer:
    def __init__(self, metadata: Optional[MetadataProvider] = None) -> None:
        self.metadata = metadata

    def analyze(self, sql: str) -> AnalysisResult:
        sql = sql.strip()
        result = AnalysisResult(original_sql=sql, metadata_used=self.metadata is not None)

        try:
            parsed = sqlglot.parse(sql, dialect="bigquery")
        except Exception as e:
            result.parse_error = str(e)
            result.rewritten_sql = sql
            result.findings.append(Finding(
                rule_id="PARSE_ERROR",
                title="SQL parse error",
                severity=Severity.CRITICAL,
                description=f"Could not parse SQL: {e}",
                recommendation="Fix syntax errors before running optimization analysis.",
            ))
            return result

        statements = [s for s in parsed if s is not None]
        result.statement_count = len(statements)
        context = AnalysisContext(statements=statements, metadata=self.metadata, raw_sql=sql)

        # Statement-level rules: once per top-level statement.
        for statement in statements:
            stmt_sql = statement.sql(dialect="bigquery")
            for rule in STATEMENT_RULES:
                try:
                    result.findings.extend(rule.analyze(statement, stmt_sql, context))
                except Exception as e:
                    result.findings.append(self._rule_error(rule.rule_id, e))

        # Session-level rules: once over all statements.
        for rule in SESSION_RULES:
            try:
                result.findings.extend(rule.analyze_session(statements, context))
            except Exception as e:
                result.findings.append(self._rule_error(rule.rule_id, e))

        result.rewritten_sql = _apply_rewrites(sql, result.findings)
        return result

    @staticmethod
    def _rule_error(rule_id: str, error: Exception) -> Finding:
        return Finding(
            rule_id=f"{rule_id}_ERROR",
            title=f"Rule {rule_id} failed",
            severity=Severity.INFO,
            description=f"Rule analysis error: {error}",
            recommendation="This is a bug in the optimizer. Please report it.",
        )
