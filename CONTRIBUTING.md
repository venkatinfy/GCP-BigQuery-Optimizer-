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

```python
from typing import List
import sqlglot
import sqlglot.expressions as exp
from .base import BaseRule, Finding, Severity


class MyNewRule(BaseRule):
    rule_id = "MY_NEW_RULE"          # Unique SCREAMING_SNAKE_CASE identifier
    title = "Short human-readable title"

    def analyze(self, expression: sqlglot.Expression, original_sql: str) -> List[Finding]:
        findings: List[Finding] = []
        # Walk the AST and detect the anti-pattern
        for node in expression.find_all(exp.SomeExpression):
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

### 2. Register the rule

In `bq_optimizer/rules/__init__.py`:

1. Add an import: `from .my_new_rule import MyNewRule`
2. Add to `ALL_RULES`: `MyNewRule(),`
3. Add to `__all__`

### 3. Write tests

Add a test file or extend `tests/test_rules.py`:

```python
from bq_optimizer.rules.my_new_rule import MyNewRule

def test_my_new_rule_detects():
    rule = MyNewRule()
    sql = "... SQL that triggers the rule ..."
    findings = rule.analyze(sqlglot.parse_one(sql, dialect="bigquery"), sql)
    assert len(findings) >= 1
    assert findings[0].rule_id == "MY_NEW_RULE"

def test_my_new_rule_clean():
    rule = MyNewRule()
    sql = "... SQL that should NOT trigger the rule ..."
    findings = rule.analyze(sqlglot.parse_one(sql, dialect="bigquery"), sql)
    assert findings == []
```

### 4. Update the README

Add a row to the **Rules** table in `README.md`.

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
