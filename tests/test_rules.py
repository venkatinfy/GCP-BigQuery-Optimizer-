"""Unit tests for individual optimization rules."""

import pytest
import sqlglot

from bq_optimizer.rules.select_star import SelectStarRule
from bq_optimizer.rules.order_by_without_limit import OrderByWithoutLimitRule
from bq_optimizer.rules.cross_join import CrossJoinRule
from bq_optimizer.rules.partition_filter import PartitionFilterRule
from bq_optimizer.rules.repeated_subquery import RepeatedSubqueryRule
from bq_optimizer.rules.count_distinct import CountDistinctRule
from bq_optimizer.rules.scalar_subquery_in_select import ScalarSubqueryInSelectRule
from bq_optimizer.rules.null_comparison import NullComparisonRule
from bq_optimizer.rules.like_leading_wildcard import LikeLeadingWildcardRule
from bq_optimizer.rules.unnecessary_distinct import UnnecessaryDistinctRule


def _parse(sql: str):
    return sqlglot.parse_one(sql, dialect="bigquery")


# ---------------------------------------------------------------------------
# SelectStarRule
# ---------------------------------------------------------------------------

def test_select_star_detects():
    rule = SelectStarRule()
    findings = rule.analyze(_parse("SELECT * FROM `p.d.t`"), "SELECT * FROM `p.d.t`")
    assert len(findings) == 1
    assert findings[0].rule_id == "SELECT_STAR"


def test_select_star_clean():
    rule = SelectStarRule()
    findings = rule.analyze(_parse("SELECT id, name FROM `p.d.t`"), "SELECT id, name FROM `p.d.t`")
    assert findings == []


# ---------------------------------------------------------------------------
# OrderByWithoutLimitRule
# ---------------------------------------------------------------------------

def test_order_by_without_limit_detects():
    rule = OrderByWithoutLimitRule()
    sql = "SELECT id FROM t ORDER BY id"
    findings = rule.analyze(_parse(sql), sql)
    assert len(findings) >= 1
    assert findings[0].rule_id == "ORDER_BY_WITHOUT_LIMIT"


def test_order_by_with_limit_clean():
    rule = OrderByWithoutLimitRule()
    sql = "SELECT id FROM t ORDER BY id LIMIT 100"
    findings = rule.analyze(_parse(sql), sql)
    assert findings == []


# ---------------------------------------------------------------------------
# CrossJoinRule
# ---------------------------------------------------------------------------

def test_cross_join_detects():
    rule = CrossJoinRule()
    sql = "SELECT a.id FROM a CROSS JOIN b"
    findings = rule.analyze(_parse(sql), sql)
    assert len(findings) == 1
    assert findings[0].rule_id == "CROSS_JOIN"


def test_cross_join_clean():
    rule = CrossJoinRule()
    sql = "SELECT a.id FROM a INNER JOIN b ON a.id = b.id"
    findings = rule.analyze(_parse(sql), sql)
    assert findings == []


# ---------------------------------------------------------------------------
# PartitionFilterRule
# ---------------------------------------------------------------------------

def test_partition_filter_detects():
    rule = PartitionFilterRule()
    sql = "SELECT * FROM user_events"
    findings = rule.analyze(_parse(sql), sql)
    assert len(findings) >= 1
    assert findings[0].rule_id == "PARTITION_FILTER"


def test_partition_filter_clean():
    rule = PartitionFilterRule()
    sql = "SELECT * FROM user_events WHERE event_date = '2024-01-01'"
    findings = rule.analyze(_parse(sql), sql)
    assert findings == []


# ---------------------------------------------------------------------------
# RepeatedSubqueryRule
# ---------------------------------------------------------------------------

def test_repeated_subquery_detects():
    rule = RepeatedSubqueryRule()
    sql = """
    SELECT a.id
    FROM (SELECT id FROM base WHERE x = 1) a
    JOIN (SELECT id FROM base WHERE x = 1) b ON a.id = b.id
    """
    findings = rule.analyze(_parse(sql), sql)
    assert len(findings) >= 1
    assert findings[0].rule_id == "REPEATED_SUBQUERY"


def test_repeated_subquery_clean():
    rule = RepeatedSubqueryRule()
    sql = "SELECT id FROM (SELECT id FROM base WHERE x = 1) a"
    findings = rule.analyze(_parse(sql), sql)
    assert findings == []


# ---------------------------------------------------------------------------
# CountDistinctRule
# ---------------------------------------------------------------------------

def test_count_distinct_detects():
    rule = CountDistinctRule()
    sql = "SELECT COUNT(DISTINCT user_id) FROM events"
    findings = rule.analyze(_parse(sql), sql)
    assert len(findings) == 1
    assert findings[0].rule_id == "COUNT_DISTINCT"


def test_count_distinct_clean():
    rule = CountDistinctRule()
    sql = "SELECT COUNT(user_id) FROM events"
    findings = rule.analyze(_parse(sql), sql)
    assert findings == []


# ---------------------------------------------------------------------------
# ScalarSubqueryInSelectRule
# ---------------------------------------------------------------------------

def test_scalar_subquery_in_select_detects():
    rule = ScalarSubqueryInSelectRule()
    sql = "SELECT id, (SELECT MAX(score) FROM scores WHERE scores.user_id = users.id) FROM users"
    findings = rule.analyze(_parse(sql), sql)
    assert len(findings) >= 1
    assert findings[0].rule_id == "SCALAR_SUBQUERY_IN_SELECT"


def test_scalar_subquery_in_select_clean():
    rule = ScalarSubqueryInSelectRule()
    sql = "SELECT id, name FROM users"
    findings = rule.analyze(_parse(sql), sql)
    assert findings == []


# ---------------------------------------------------------------------------
# NullComparisonRule
# ---------------------------------------------------------------------------

def test_null_comparison_detects():
    rule = NullComparisonRule()
    sql = "SELECT * FROM t WHERE col = NULL"
    findings = rule.analyze(_parse(sql), sql)
    assert len(findings) >= 1
    assert findings[0].rule_id == "NULL_COMPARISON"


def test_null_comparison_clean():
    rule = NullComparisonRule()
    sql = "SELECT * FROM t WHERE col IS NULL"
    findings = rule.analyze(_parse(sql), sql)
    assert findings == []


# ---------------------------------------------------------------------------
# LikeLeadingWildcardRule
# ---------------------------------------------------------------------------

def test_like_leading_wildcard_detects():
    rule = LikeLeadingWildcardRule()
    sql = "SELECT * FROM t WHERE name LIKE '%foo'"
    findings = rule.analyze(_parse(sql), sql)
    assert len(findings) >= 1
    assert findings[0].rule_id == "LIKE_LEADING_WILDCARD"


def test_like_leading_wildcard_clean():
    rule = LikeLeadingWildcardRule()
    sql = "SELECT * FROM t WHERE name LIKE 'foo%'"
    findings = rule.analyze(_parse(sql), sql)
    assert findings == []


# ---------------------------------------------------------------------------
# UnnecessaryDistinctRule
# ---------------------------------------------------------------------------

def test_unnecessary_distinct_detects():
    rule = UnnecessaryDistinctRule()
    sql = "SELECT DISTINCT user_id, status FROM events GROUP BY user_id, status"
    findings = rule.analyze(_parse(sql), sql)
    assert len(findings) >= 1
    assert findings[0].rule_id == "UNNECESSARY_DISTINCT"


def test_unnecessary_distinct_clean():
    rule = UnnecessaryDistinctRule()
    sql = "SELECT DISTINCT user_id FROM events"
    findings = rule.analyze(_parse(sql), sql)
    assert findings == []
