from .base import BaseRule, SessionRule, Finding, Severity

# --- Statement-level rules (run once per top-level statement) ----------------
from .select_star import SelectStarRule
from .order_by_without_limit import OrderByWithoutLimitRule
from .cross_join import CrossJoinRule
from .partition_filter import PartitionFilterRule
from .repeated_subquery import RepeatedSubqueryRule
from .count_distinct import CountDistinctRule
from .scalar_subquery_in_select import ScalarSubqueryInSelectRule
from .null_comparison import NullComparisonRule
from .like_leading_wildcard import LikeLeadingWildcardRule
from .unnecessary_distinct import UnnecessaryDistinctRule
from .redundant_scans import RedundantScansRule
from .truncate_dml import TruncateDmlRule
from .large_in_clause import LargeInClauseRule
from .table_cloning import TableCloningRule
from .string_comparison import StringComparisonRule
from .suboptimal_join_keys import SuboptimalJoinKeysRule
from .native_conversion import NativeConversionRule
from .join_ordering import JoinOrderingRule
from .unfiltered_partition import UnfilteredPartitionRule

# --- Session-level rules (run once over all statements together) -------------
from .merge_optimization import MergeOptimizationRule
from .redundant_updates import RedundantUpdatesRule
from .resource_failures import ResourceFailuresRule


STATEMENT_RULES = [
    SelectStarRule(),
    OrderByWithoutLimitRule(),
    CrossJoinRule(),
    PartitionFilterRule(),
    RepeatedSubqueryRule(),
    CountDistinctRule(),
    ScalarSubqueryInSelectRule(),
    NullComparisonRule(),
    LikeLeadingWildcardRule(),
    UnnecessaryDistinctRule(),
    RedundantScansRule(),
    TruncateDmlRule(),
    LargeInClauseRule(),
    TableCloningRule(),
    StringComparisonRule(),
    SuboptimalJoinKeysRule(),
    NativeConversionRule(),
    JoinOrderingRule(),
    UnfilteredPartitionRule(),
]

SESSION_RULES = [
    MergeOptimizationRule(),
    RedundantUpdatesRule(),
    ResourceFailuresRule(),
]

# Backwards-compatible alias: the statement rules.
ALL_RULES = STATEMENT_RULES

__all__ = [
    "BaseRule", "SessionRule", "Finding", "Severity",
    "STATEMENT_RULES", "SESSION_RULES", "ALL_RULES",
    "SelectStarRule", "OrderByWithoutLimitRule", "CrossJoinRule",
    "PartitionFilterRule", "RepeatedSubqueryRule", "CountDistinctRule",
    "ScalarSubqueryInSelectRule", "NullComparisonRule",
    "LikeLeadingWildcardRule", "UnnecessaryDistinctRule",
    "RedundantScansRule", "TruncateDmlRule", "LargeInClauseRule",
    "TableCloningRule", "StringComparisonRule", "SuboptimalJoinKeysRule",
    "NativeConversionRule", "JoinOrderingRule", "UnfilteredPartitionRule",
    "MergeOptimizationRule", "RedundantUpdatesRule", "ResourceFailuresRule",
]
