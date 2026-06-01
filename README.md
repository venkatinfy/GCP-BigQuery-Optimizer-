# bq-optimizer

![Python](https://img.shields.io/badge/python-3.9%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![PyPI-ready](https://img.shields.io/badge/PyPI-ready-brightgreen)

**bq-optimizer** is a command-line tool that performs systematic, rule-based analysis of BigQuery SQL queries. It identifies common anti-patterns and performance pitfalls — such as `SELECT *`, missing partition filters, incorrect NULL comparisons, and costly `CROSS JOIN`s — and produces a detailed report with severity ratings, explanations, and a rewritten query incorporating safe fixes and inline suggestions.

---

## Features

- 10 built-in optimization rules covering correctness, performance, and cost
- Parses SQL using [sqlglot](https://github.com/tobymao/sqlglot) with BigQuery dialect support
- Generates a rich text report (with optional ANSI colors) or a self-contained HTML report
- Applies safe automatic rewrites (NULL comparisons, redundant DISTINCT, etc.)
- JSON output mode for integration with CI/CD pipelines
- Reads queries from `--query`, `--file`, or stdin
- Exits with code 2 when CRITICAL findings are present (useful in pipelines)

---

## Installation

### From PyPI (once published)

```bash
pip install bq-optimizer
```

### From source

```bash
git clone https://github.com/your-org/GCP-BigQuery-Optimizer-.git
cd GCP-BigQuery-Optimizer-
pip install -e .
```

### Requirements

- Python 3.9+
- sqlglot >= 20.0.0 (installed automatically)

---

## Quick Start

### Analyze a query string

```bash
bq-optimizer --query "SELECT *, COUNT(DISTINCT id) FROM \`project.dataset.events\` ORDER BY created_at"
```

Sample output:

```
==================================================
  BigQuery Query Optimizer Report
==================================================

ORIGINAL QUERY:
  SELECT *, COUNT(DISTINCT id) FROM `project.dataset.events` ORDER BY created_at

ANALYSIS SUMMARY:
  Total findings: 4
  Critical: 0  |  Warnings: 3  |  Info: 1

FINDINGS:
  [1] WARNING - SELECT_STAR
      Title: SELECT * usage detected
      Description: SELECT * retrieves all columns, increasing bytes scanned and cost.
      Recommendation: Explicitly list only required columns...
      ...

OPTIMIZED QUERY:
  SELECT *, COUNT(DISTINCT id) /* SUGGESTION: APPROX_COUNT_DISTINCT(id) */
  FROM `project.dataset.events` -- SUGGESTION: add partition filter in WHERE clause
  ORDER BY created_at -- SUGGESTION: add LIMIT

==================================================
  End of Report
==================================================
```

### Read from a file

```bash
bq-optimizer --file examples/sample_queries.sql
```

### Read from stdin

```bash
cat my_query.sql | bq-optimizer
```

### Generate an HTML report

```bash
bq-optimizer --file query.sql --output-html report.html
```

### JSON output for CI/CD

```bash
bq-optimizer --query "SELECT * FROM t" --format json | jq '.summary'
```

### Disable colors

```bash
bq-optimizer --query "SELECT * FROM t" --no-color
```

---

## Rules

| Rule ID | Severity | What it detects | Recommendation summary |
|---------|----------|----------------|------------------------|
| `SELECT_STAR` | WARNING | `SELECT *` or `SELECT t.*` | List only required columns |
| `ORDER_BY_WITHOUT_LIMIT` | WARNING | `ORDER BY` at top level without `LIMIT` | Add `LIMIT` or remove `ORDER BY` |
| `CROSS_JOIN` | CRITICAL | `CROSS JOIN` or implicit cartesian product | Use `INNER JOIN ... ON` instead |
| `PARTITION_FILTER` | WARNING | Queries on partitioned tables without a partition filter | Add `WHERE` filter on partition column |
| `REPEATED_SUBQUERY` | WARNING | Identical subquery text appearing more than once | Extract into a CTE (`WITH` clause) |
| `COUNT_DISTINCT` | INFO | `COUNT(DISTINCT col)` | Consider `APPROX_COUNT_DISTINCT` (~1% error, faster) |
| `SCALAR_SUBQUERY_IN_SELECT` | CRITICAL | Correlated subquery in `SELECT` list | Rewrite as `JOIN` or window function |
| `NULL_COMPARISON` | CRITICAL | `col = NULL` or `col != NULL` | Use `IS NULL` / `IS NOT NULL` |
| `LIKE_LEADING_WILDCARD` | INFO | `LIKE '%pattern'` (leading wildcard) | Use `REGEXP_CONTAINS` or restructure filter |
| `UNNECESSARY_DISTINCT` | INFO | `SELECT DISTINCT` combined with `GROUP BY` | Remove `DISTINCT` (redundant) |

---

## Report formats

### Text (default)

A human-readable report with color-coded severity levels printed to stdout. Use `--no-color` to disable ANSI escape codes.

### HTML

A self-contained HTML file with no external dependencies. Features:

- Summary cards showing counts by severity (color-coded red/orange/blue)
- Collapsible findings accordion with original and suggested SQL snippets
- Original query and optimized query displayed in syntax-highlighted `<pre>` blocks
- Copy-to-clipboard button for the optimized query

Generate with: `bq-optimizer --file query.sql --output-html report.html`

The HTML report opens directly in any browser. The optimized query section includes a "Copy to clipboard" button for easy use.

### JSON

Machine-readable output suitable for CI/CD integration. Includes the full findings list with all metadata plus the rewritten SQL.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to set up the dev environment, add new rules, write tests, and submit pull requests.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
