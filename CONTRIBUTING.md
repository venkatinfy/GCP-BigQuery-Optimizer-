# Contributing to bq-optimizer

Thank you for your interest in contributing! This guide explains how to set up the development environment, add new rules, run tests, and submit a pull request.

---

## Setting up the development environment

```bash
# Clone the repository
git clone https://github.com/your-org/GCP-BigQuery-Optimizer-.git
cd GCP-BigQuery-Optimizer-

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e .
pip install pytest
```

---

## Running tests

```bash
python -m pytest tests/ -v
```

All tests should pass before submitting a PR.

---

## Adding a new rule

Each optimization rule lives in `bq_optimizer/rules/` as its own module. Follow these steps:

### 1. Create the rule file

Create `bq_optimizer/rules/my_new_rule.py` using this template:

There are two kinds of rule:

- **Statement-level** rules subclass `BaseRule` and are invoked once per top-level
  statement via `analyze(expression, original_sql, context)`.
- **Session-level** rules subclass `SessionRule` and are invoked once over *all*
  statements via `analyze_session(statements, context)` — use these for patterns
  that only emerge across statements (e.g. INSERT+UPDATE → MERGE).

```python
from typing import List
import sqlglot.expressions as exp
from .base import BaseRule, Finding, Severity


class MyNewRule(BaseRule):
    rule_id = "MY_NEW_RULE"          # Unique SCREAMING_SNAKE_CASE identifier
    title = "Short human-readable title"
    requires_metadata = False        # set True if the rule needs INFORMATION_SCHEMA

    def analyze(self, expression: exp.Expression, original_sql: str, context=None) -> List[Finding]:
        findings: List[Finding] = []
        # Walk the AST and detect the anti-pattern
        for node in expression.find_all(exp.Column):
            findings.append(Finding(
                rule_id=self.rule_id,
                title=self.title,
                severity=Severity.WARNING,  # or CRITICAL / INFO
                description="Explain what was found and why it is a problem.",
                recommendation="Explain how to fix it.",
                original_snippet="the bad SQL fragment",
                suggested_snippet="the improved SQL fragment",
            ))
        return findings
```

#### Metadata-aware rules

Set `requires_metadata = True` and read from `context.metadata` (a
`MetadataProvider`). **Always degrade gracefully** — return `[]` (never raise)
when metadata is unavailable:

```python
def analyze(self, expression, original_sql, context=None):
    if context is None or context.metadata is None:
        return []
    table = context.metadata.get_table("project.dataset.table")
    ...
```

Helpers in `bq_optimizer/util.py` (`table_fqn`, `build_alias_map`,
`physical_tables`, …) handle table-name normalization and alias resolution.

#### Session-level rules

```python
from .base import SessionRule, Finding, Severity

class MySessionRule(SessionRule):
    rule_id = "MY_SESSION_RULE"
    title = "..."

    def analyze_session(self, statements, context) -> List[Finding]:
        # Reason across every statement in `statements`.
        return []
```

### 2. Register the rule

In `bq_optimizer/rules/__init__.py`:

1. Add an import: `from .my_new_rule import MyNewRule`
2. Add it to `STATEMENT_RULES` (or `SESSION_RULES` for a `SessionRule`)
3. Add it to `__all__`

### 3. Write tests

Add tests to `tests/test_new_rules.py` (build an `AnalysisContext`, with a
`StaticMetadataProvider` when the rule needs metadata):

```python
import sqlglot
from bq_optimizer.context import AnalysisContext
from bq_optimizer.rules.my_new_rule import MyNewRule

def _ctx(sql, metadata=None):
    stmts = [s for s in sqlglot.parse(sql, dialect="bigquery") if s is not None]
    return AnalysisContext(statements=stmts, metadata=metadata, raw_sql=sql)

def test_my_new_rule_detects():
    sql = "... SQL that triggers the rule ..."
    findings = MyNewRule().analyze(sqlglot.parse_one(sql, dialect="bigquery"), sql, _ctx(sql))
    assert findings and findings[0].rule_id == "MY_NEW_RULE"
```

### 4. Update the README

Add a row to the appropriate **Rules** table in `README.md` (and the
`INFORMATION_SCHEMA` mapping table if the rule consumes metadata).

---

## Severity guidelines

| Severity | When to use |
|----------|-------------|
| `CRITICAL` | Produces incorrect results OR extreme performance impact (e.g. cartesian product, NULL equality) |
| `WARNING`  | Significant performance impact or common mistake (e.g. SELECT *, missing partition filter) |
| `INFO`     | Suggestion for further optimization with trade-offs (e.g. APPROX_COUNT_DISTINCT) |

---

## Pull request process

1. Fork the repository and create a feature branch: `git checkout -b feature/my-new-rule`
2. Make your changes and ensure all tests pass.
3. Commit with a descriptive message.
4. Push and open a pull request against `main`.
5. A maintainer will review and merge.

---

## Code style

- Python 3.9+ compatible
- Type hints required on all public functions and methods
- Keep rule logic focused and testable (one rule per file)
- Use `sqlglot` for all SQL parsing — never use raw string manipulation for AST traversal
