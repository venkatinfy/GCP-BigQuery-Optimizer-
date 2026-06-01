"""Tests for the enterprise optimization rules (v0.2)."""

import sqlglot

from bq_optimizer import QueryAnalyzer, StaticMetadataProvider
from bq_optimizer.context import AnalysisContext
from bq_optimizer.rules.redundant_scans import RedundantScansRule
from bq_optimizer.rules.truncate_dml import TruncateDmlRule
from bq_optimizer.rules.large_in_clause import LargeInClauseRule
from bq_optimizer.rules.table_cloning import TableCloningRule
from bq_optimizer.rules.string_comparison import StringComparisonRule
from bq_optimizer.rules.unfiltered_partition import UnfilteredPartitionRule
from bq_optimizer.rules.suboptimal_join_keys import SuboptimalJoinKeysRule
from bq_optimizer.rules.native_conversion import NativeConversionRule
from bq_optimizer.rules.join_ordering import JoinOrderingRule
from bq_optimizer.rules.merge_optimization import MergeOptimizationRule
from bq_optimizer.rules.redundant_updates import RedundantUpdatesRule
from bq_optimizer.rules.resource_failures import ResourceFailuresRule


def _parse(sql):
    return sqlglot.parse_one(sql, dialect="bigquery")


def _ctx(sql, metadata=None):
    stmts = [s for s in sqlglot.parse(sql, dialect="bigquery") if s is not None]
    return AnalysisContext(statements=stmts, metadata=metadata, raw_sql=sql)


# --- AST-only statement rules -------------------------------------------------

def test_redundant_scans_detects_self_join():
    sql = "SELECT a.id FROM `p.d.t` a JOIN `p.d.t` b ON a.id = b.id"
    findings = RedundantScansRule().analyze(_parse(sql), sql)
    assert any(f.rule_id == "REDUNDANT_SCANS" for f in findings)


def test_redundant_scans_clean():
    sql = "SELECT a.id FROM `p.d.t` a JOIN `p.d.s` b ON a.id = b.id"
    assert RedundantScansRule().analyze(_parse(sql), sql) == []


def test_truncate_dml_detects_unbounded_delete():
    sql = "DELETE FROM `p.d.t`"
    findings = TruncateDmlRule().analyze(_parse(sql), sql)
    assert findings and findings[0].rule_id == "TRUNCATE_DML"
    assert "TRUNCATE" in findings[0].suggested_snippet


def test_truncate_dml_where_true_flagged():
    sql = "DELETE FROM `p.d.t` WHERE 1 = 1"
    assert TruncateDmlRule().analyze(_parse(sql), sql)


def test_truncate_dml_clean_with_filter():
    sql = "DELETE FROM `p.d.t` WHERE id = 5"
    assert TruncateDmlRule().analyze(_parse(sql), sql) == []


def test_large_in_clause_detects():
    values = ",".join(str(i) for i in range(60))
    sql = f"SELECT id FROM t WHERE id IN ({values})"
    findings = LargeInClauseRule().analyze(_parse(sql), sql)
    assert findings and findings[0].rule_id == "LARGE_IN_CLAUSE"


def test_large_in_clause_small_is_clean():
    sql = "SELECT id FROM t WHERE id IN (1, 2, 3)"
    assert LargeInClauseRule().analyze(_parse(sql), sql) == []


def test_table_cloning_detects():
    sql = "CREATE TABLE `p.d.copy` AS SELECT * FROM `p.d.src`"
    findings = TableCloningRule().analyze(_parse(sql), sql)
    assert findings and "CLONE" in findings[0].suggested_snippet


def test_table_cloning_clean_with_transform():
    sql = "CREATE TABLE `p.d.copy` AS SELECT * FROM `p.d.src` WHERE x = 1"
    assert TableCloningRule().analyze(_parse(sql), sql) == []


def test_string_comparison_detects():
    sql = "SELECT id FROM users WHERE UPPER(name) = 'BOB'"
    findings = StringComparisonRule().analyze(_parse(sql), sql)
    assert findings and findings[0].rule_id == "STRING_COMPARISON"


def test_string_comparison_clean_in_select_only():
    sql = "SELECT LOWER(name) AS n FROM users"
    assert StringComparisonRule().analyze(_parse(sql), sql) == []


def test_unfiltered_partition_no_metadata_advisory():
    sql = "SELECT * FROM a EXCEPT DISTINCT SELECT * FROM b"
    findings = UnfilteredPartitionRule().analyze(_parse(sql), sql, _ctx(sql))
    assert findings and findings[0].rule_id == "UNFILTERED_PARTITION"


# --- metadata-aware statement rules ------------------------------------------

def _meta():
    return StaticMetadataProvider({
        "tables": {
            "p.d.users": {"table_type": "BASE TABLE", "size_bytes": 1000,
                           "columns": {"id": {"data_type": "STRING"}}},
            "p.d.orders": {"table_type": "BASE TABLE", "size_bytes": 9000,
                            "columns": {"uid": {"data_type": "STRING"}}},
            "p.d.ext": {"table_type": "EXTERNAL", "size_bytes": 5000,
                         "columns": {"k": {"data_type": "INT64"}}},
            "p.d.facts": {"table_type": "BASE TABLE", "partition_column": "dt",
                           "columns": {"dt": {"data_type": "DATE", "is_partitioning_column": True}}},
        },
        "jobs": [{"job_id": "job_1", "state": "DONE",
                   "error_reason": "resourcesExceeded",
                   "error_message": "Resources exceeded during query execution."}],
    })


def test_suboptimal_join_keys_requires_metadata():
    sql = "SELECT u.id FROM `p.d.users` u JOIN `p.d.orders` o ON u.id = o.uid"
    assert SuboptimalJoinKeysRule().analyze(_parse(sql), sql, _ctx(sql)) == []  # no metadata
    findings = SuboptimalJoinKeysRule().analyze(_parse(sql), sql, _ctx(sql, _meta()))
    assert any(f.rule_id == "SUBOPTIMAL_JOIN_KEYS" for f in findings)


def test_native_conversion_detects_external_in_join():
    sql = "SELECT u.id FROM `p.d.users` u JOIN `p.d.ext` e ON e.k = u.id"
    findings = NativeConversionRule().analyze(_parse(sql), sql, _ctx(sql, _meta()))
    assert any(f.rule_id == "NATIVE_CONVERSION" for f in findings)


def test_join_ordering_recommends_largest_first():
    sql = ("SELECT u.id FROM `p.d.users` u "
           "JOIN `p.d.orders` o ON u.id = o.uid "
           "JOIN `p.d.ext` e ON e.k = u.id")
    findings = JoinOrderingRule().analyze(_parse(sql), sql, _ctx(sql, _meta()))
    assert findings and findings[0].suggested_snippet.startswith("FROM p.d.orders")


# --- session rules ------------------------------------------------------------

def test_merge_optimization_detects_insert_plus_update():
    sql = ("INSERT INTO `p.d.t` (id) SELECT id FROM s; "
           "UPDATE `p.d.t` SET v = 1 WHERE id = 2;")
    ctx = _ctx(sql)
    findings = MergeOptimizationRule().analyze_session(ctx.statements, ctx)
    assert findings and findings[0].rule_id == "MERGE_OPTIMIZATION"


def test_redundant_updates_detects_repeat():
    sql = ("UPDATE `p.d.t` SET a = 1 WHERE id = 1; "
           "UPDATE `p.d.t` SET b = 2 WHERE id = 1;")
    ctx = _ctx(sql)
    findings = RedundantUpdatesRule().analyze_session(ctx.statements, ctx)
    assert findings and findings[0].rule_id == "REDUNDANT_UPDATES"


def test_resource_failures_from_metadata():
    ctx = _ctx("SELECT 1", _meta())
    findings = ResourceFailuresRule().analyze_session(ctx.statements, ctx)
    assert findings and findings[0].severity.value == "CRITICAL"


def test_resource_failures_no_metadata_is_silent():
    ctx = _ctx("SELECT 1")
    assert ResourceFailuresRule().analyze_session(ctx.statements, ctx) == []


# --- end-to-end ---------------------------------------------------------------

def test_analyzer_multi_statement_session_rules():
    sql = ("INSERT INTO `p.d.t` (id) SELECT id FROM s; "
           "UPDATE `p.d.t` SET v = 1 WHERE id = 2; "
           "UPDATE `p.d.t` SET v = 2 WHERE id = 3;")
    result = QueryAnalyzer().analyze(sql)
    assert result.statement_count == 3
    ids = {f.rule_id for f in result.findings}
    assert "MERGE_OPTIMIZATION" in ids
    assert "REDUNDANT_UPDATES" in ids


def test_analyzer_metadata_flag_recorded():
    assert QueryAnalyzer().analyze("SELECT 1").metadata_used is False
    assert QueryAnalyzer(metadata=_meta()).analyze("SELECT 1").metadata_used is True
