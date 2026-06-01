from dataclasses import dataclass, field
from typing import List, Optional
import re
import sqlglot
import sqlglot.expressions as exp

from .rules import ALL_RULES, Finding, Severity


@dataclass
class AnalysisResult:
    original_sql: str
    findings: List[Finding] = field(default_factory=list)
    rewritten_sql: str = ""
    parse_error: Optional[str] = None

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


def _apply_rewrites(sql: str, expression: exp.Expression, findings: List[Finding]) -> str:
    """Apply safe textual rewrites and suggestion comments to the SQL."""
    result = sql

    # Fix NULL comparisons: col = NULL -> col IS NULL
    result = re.sub(r'(\w+)\s*=\s*NULL\b', r'\1 IS NULL', result, flags=re.IGNORECASE)
    result = re.sub(r'(\w+)\s*!=\s*NULL\b', r'\1 IS NOT NULL', result, flags=re.IGNORECASE)
    result = re.sub(r'(\w+)\s*<>\s*NULL\b', r'\1 IS NOT NULL', result, flags=re.IGNORECASE)

    # Remove DISTINCT when GROUP BY present (simple regex-based approach)
    has_group_by = bool(re.search(r'\bGROUP\s+BY\b', result, re.IGNORECASE))
    if has_group_by:
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

    # Add partition filter suggestion comment after FROM if partition filter missing
    partition_findings = [f for f in findings if f.rule_id == "PARTITION_FILTER"]
    if partition_findings:
        result = re.sub(
            r'(\bFROM\b\s+`?[\w.]+`?)',
            r'\1 -- SUGGESTION: add partition filter in WHERE clause',
            result,
            count=1,
            flags=re.IGNORECASE,
        )

    # Replace COUNT(DISTINCT x) with a comment suggesting APPROX_COUNT_DISTINCT
    def replace_count_distinct(m: re.Match) -> str:
        inner = m.group(1)
        return f"COUNT(DISTINCT {inner}) /* SUGGESTION: APPROX_COUNT_DISTINCT({inner}) */"

    result = re.sub(
        r'\bCOUNT\s*\(\s*DISTINCT\s+([^)]+)\)',
        replace_count_distinct,
        result,
        flags=re.IGNORECASE,
    )

    return result


class QueryAnalyzer:
    def analyze(self, sql: str) -> AnalysisResult:
        sql = sql.strip()
        result = AnalysisResult(original_sql=sql)

        try:
            expression = sqlglot.parse_one(sql, dialect="bigquery")
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

        for rule in ALL_RULES:
            try:
                findings = rule.analyze(expression, sql)
                result.findings.extend(findings)
            except Exception as e:
                result.findings.append(Finding(
                    rule_id=f"{rule.rule_id}_ERROR",
                    title=f"Rule {rule.rule_id} failed",
                    severity=Severity.INFO,
                    description=f"Rule analysis error: {e}",
                    recommendation="This is a bug in the optimizer. Please report it.",
                ))

        result.rewritten_sql = _apply_rewrites(sql, expression, result.findings)
        return result
