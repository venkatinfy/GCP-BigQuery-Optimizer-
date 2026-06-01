"""End-to-end tests for QueryAnalyzer."""

import pytest
from bq_optimizer.analyzer import QueryAnalyzer
from bq_optimizer.rules.base import Severity


def test_analyzer_complex_bad_query():
    sql = """
    SELECT DISTINCT *, COUNT(DISTINCT user_id)
    FROM `project.dataset.user_events`
    WHERE status = NULL
    ORDER BY created_at
    GROUP BY user_id, status
    """
    analyzer = QueryAnalyzer()
    result = analyzer.analyze(sql)

    assert result.original_sql.strip() == sql.strip()
    assert result.total_count > 0
    # Should have critical finding for NULL comparison
    rule_ids = {f.rule_id for f in result.findings}
    assert "NULL_COMPARISON" in rule_ids
    # Should flag SELECT *
    assert "SELECT_STAR" in rule_ids
    # rewritten SQL should be present
    assert result.rewritten_sql


def test_analyzer_clean_query():
    sql = "SELECT id, name FROM users WHERE created_at >= '2024-01-01' LIMIT 100"
    analyzer = QueryAnalyzer()
    result = analyzer.analyze(sql)
    assert result.parse_error is None
    # Should have few or no critical findings
    assert result.critical_count == 0


def test_analyzer_parse_error_graceful():
    sql = "SELECT FROM WHERE !!!"
    analyzer = QueryAnalyzer()
    result = analyzer.analyze(sql)
    # Should not raise; may have a parse error finding or just return with results
    assert result.rewritten_sql is not None


def test_analyzer_order_by_without_limit():
    sql = "SELECT id FROM t ORDER BY id"
    analyzer = QueryAnalyzer()
    result = analyzer.analyze(sql)
    rule_ids = {f.rule_id for f in result.findings}
    assert "ORDER_BY_WITHOUT_LIMIT" in rule_ids
    assert "SUGGESTION: add LIMIT" in result.rewritten_sql


def test_analyzer_count_distinct_rewrite():
    sql = "SELECT COUNT(DISTINCT id) FROM t"
    analyzer = QueryAnalyzer()
    result = analyzer.analyze(sql)
    assert "APPROX_COUNT_DISTINCT" in result.rewritten_sql


def test_analyzer_null_comparison_rewrite():
    sql = "SELECT * FROM t WHERE col = NULL"
    analyzer = QueryAnalyzer()
    result = analyzer.analyze(sql)
    assert "IS NULL" in result.rewritten_sql


def test_analyzer_result_severity_counts():
    sql = "SELECT * FROM t WHERE col = NULL ORDER BY id"
    analyzer = QueryAnalyzer()
    result = analyzer.analyze(sql)
    assert result.critical_count + result.warning_count + result.info_count == result.total_count
