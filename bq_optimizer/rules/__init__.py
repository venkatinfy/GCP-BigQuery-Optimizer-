from .base import BaseRule, Finding, Severity
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

ALL_RULES = [
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
]

__all__ = [
    "BaseRule", "Finding", "Severity",
    "SelectStarRule", "OrderByWithoutLimitRule", "CrossJoinRule",
    "PartitionFilterRule", "RepeatedSubqueryRule", "CountDistinctRule",
    "ScalarSubqueryInSelectRule", "NullComparisonRule",
    "LikeLeadingWildcardRule", "UnnecessaryDistinctRule",
    "ALL_RULES",
]
