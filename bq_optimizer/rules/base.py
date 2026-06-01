from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
from typing import List
import sqlglot
import sqlglot.expressions as exp


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
    rule_id: str
    title: str

    @abstractmethod
    def analyze(self, expression: exp.Expression, original_sql: str) -> List[Finding]:
        ...
