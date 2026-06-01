from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
from typing import List, Optional, TYPE_CHECKING
import sqlglot
import sqlglot.expressions as exp

if TYPE_CHECKING:
    from ..context import AnalysisContext


class Severity(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class Finding:
    rule_id: str
    title: str
    severity: Severity
    description: str
    recommendation: str
    line_hint: str = ""
    original_snippet: str = ""
    suggested_snippet: str = ""


class BaseRule(ABC):
    """A statement-level rule. Invoked once per top-level statement.

    Set ``requires_metadata = True`` for rules that can only act when an
    ``INFORMATION_SCHEMA``-backed provider is supplied; such rules must still
    return ``[]`` (never raise) when ``context.metadata`` is ``None``.
    """

    rule_id: str
    title: str
    requires_metadata: bool = False

    @abstractmethod
    def analyze(
        self,
        expression: exp.Expression,
        original_sql: str,
        context: Optional["AnalysisContext"] = None,
    ) -> List[Finding]:
        ...


class SessionRule(ABC):
    """A session-level rule. Invoked once over *all* statements together.

    Used for patterns that only emerge across multiple statements in a script
    or session (e.g. an INSERT followed by an UPDATE of the same target, or the
    same table updated repeatedly).
    """

    rule_id: str
    title: str
    requires_metadata: bool = False

    @abstractmethod
    def analyze_session(
        self,
        statements: List[exp.Expression],
        context: "AnalysisContext",
    ) -> List[Finding]:
        ...
