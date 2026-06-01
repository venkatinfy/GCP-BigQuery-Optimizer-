# bq-optimizer

![Python](https://img.shields.io/badge/python-3.9%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![PyPI-ready](https://img.shields.io/badge/PyPI-ready-brightgreen)

**bq-optimizer** is a command-line tool that performs systematic, rule-based analysis of BigQuery SQL queries and multi-statement scripts. It identifies common anti-patterns and performance pitfalls — from `SELECT *` and missing partition filters to enterprise-scale concerns like external tables in joins, suboptimal join ordering, full-table `DELETE`s, and jobs that failed on resource limits — and produces a detailed report with severity ratings, explanations, and a rewritten query incorporating safe fixes and inline suggestions.

Where it helps, rules consult **BigQuery `INFORMATION_SCHEMA` metadata** (table types, sizes, column types, partition columns, and recent failed jobs) to make the same judgement an experienced reviewer would.

---

## Features

- **23 optimization rules** spanning correctness, performance, cost, and operational health
- **Metadata-aware analysis** via BigQuery `INFORMATION_SCHEMA` — live (with the `bigquery` extra) or from a static JSON fixture for offline/CI use
- **Multi-statement / session analysis** — detects cross-statement patterns (e.g. INSERT+UPDATE → `MERGE`, repeated `UPDATE`s)
- Parses SQL using [sqlglot](https://github.com/tobymao/sqlglot) with BigQuery dialect support
- Generates a rich text report (with optional ANSI colors) or a self-contained HTML report
- Applies safe automatic rewrites (NULL comparisons, redundant DISTINCT, TRUNCATE/CLONE hints, etc.)
- JSON output mode for integration with CI/CD pipelines
- Reads queries from `--query`, `--file`, or stdin
- Exits with code 2 when CRITICAL findings are present (useful in pipelines)
- Metadata-dependent rules degrade gracefully — they stay silent rather than guess when metadata is absent

---

## Installation

### From PyPI (once published)

```bash
pip install bq-optimizer
```

### From source

```bash
git clone https://github.com/venkatinfy/GCP-BigQuery-Optimizer-.git
cd GCP-BigQuery-Optimizer-
pip install -e .
```

### Optional: live BigQuery metadata

```bash
pip install "bq-optimizer[bigquery]"   # adds google-cloud-bigquery
```

### Requirements

- Python 3.9+
- sqlglot >= 20.0.0 (installed automatically)
- google-cloud-bigquery >= 3.0.0 (only for the live metadata provider; optional)

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

### Core rules (SQL-only)

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

### Enterprise rules (v0.2)

The **Meta?** column marks rules that consult `INFORMATION_SCHEMA` metadata; **Scope** marks whether a rule looks at a single statement or the whole session/script.

| Rule ID | Severity | Scope | Meta? | What it detects | Recommendation summary |
|---------|----------|-------|:----:|----------------|------------------------|
| `REDUNDANT_SCANS` | WARNING | statement | – | Same table referenced/scanned multiple times in one statement | Scan once into a CTE/temp table and reuse |
| `TRUNCATE_DML` | WARNING | statement | – | Full-table `DELETE` with no (or trivially-true) `WHERE` | Use `TRUNCATE TABLE` (free, atomic, faster) |
| `LARGE_IN_CLAUSE` | WARNING | statement | – | `IN (...)` with an excessive number of literals (≥ 50) | Stage values in a temp table and `JOIN` / `UNNEST` |
| `TABLE_CLONING` | WARNING | statement | – | `CREATE TABLE ... AS SELECT * FROM t` pure copy | Use a metadata-only `CREATE TABLE ... CLONE t` |
| `STRING_COMPARISON` | INFO | statement | – | `UPPER()`/`LOWER()` wrapping a column in a predicate | Use a case-insensitive collation (`COLLATE 'und:ci'`) |
| `UNFILTERED_PARTITION` | WARNING | statement | opt. | `EXCEPT DISTINCT` over full rows without a partition filter | Add a partition filter to each side; select only needed columns |
| `SUBOPTIMAL_JOIN_KEYS` | INFO | statement | ✓ | `STRING` columns used as join keys | Prefer `INT64` surrogate keys; align collation/clustering |
| `NATIVE_CONVERSION` | WARNING | statement | ✓ | `EXTERNAL` table used inside a join | Materialize into a native table for caching/pruning |
| `JOIN_ORDERING` | INFO | statement | ✓ | Joined tables not ordered largest-first (by size) | Reorder joins largest → smallest to reduce shuffle |
| `MERGE_OPTIMIZATION` | WARNING | session | – | `INSERT` and `UPDATE` of the same target in a session | Combine into a single atomic `MERGE` |
| `REDUNDANT_UPDATES` | WARNING | session | – | Same table updated multiple times in one execution | Consolidate into one `UPDATE`/`MERGE` |
| `RESOURCE_FAILURES` | CRITICAL | session | ✓ | Jobs that failed on resource/capacity limits | Reduce shuffle/memory; review slot reservations |

---

## Metadata (`INFORMATION_SCHEMA`)

Several enterprise rules need to know things the SQL text alone can't tell you — a column's data type, whether a table is external, how big each table is, or whether recent jobs failed on capacity. bq-optimizer reads this from a **metadata provider**.

### Static fixture (offline / CI)

Pass a JSON file modelled on `INFORMATION_SCHEMA` with `--metadata`:

```bash
bq-optimizer --file examples/enterprise_queries.sql --metadata examples/sample_metadata.json
```

```json
{
  "tables": {
    "project.dataset.orders": {
      "table_type": "BASE TABLE",
      "row_count": 250000000,
      "size_bytes": 64000000000,
      "partition_column": "order_date",
      "columns": {
        "order_id":  {"data_type": "INT64"},
        "user_key":  {"data_type": "STRING"},
        "order_date":{"data_type": "DATE", "is_partitioning_column": true}
      }
    }
  },
  "jobs": [
    {"job_id": "bquxjob_1", "state": "DONE",
     "error_reason": "resourcesExceeded",
     "error_message": "Resources exceeded during query execution."}
  ]
}
```

See [`examples/sample_metadata.json`](examples/sample_metadata.json) for a complete example.

### Live BigQuery (optional)

With the `bigquery` extra installed, populate metadata directly from a project:

```python
from bq_optimizer import QueryAnalyzer
from bq_optimizer.metadata.bigquery import BigQueryMetadataProvider

provider = BigQueryMetadataProvider(
    project="my-project",
    datasets=["analytics", "staging"],
    region="region-us",
)
result = QueryAnalyzer(metadata=provider).analyze(sql)
```

### Which views are used

The exact, reviewable queries live in [`bq_optimizer/metadata/schema.py`](bq_optimizer/metadata/schema.py):

| Metadata | `INFORMATION_SCHEMA` view | Feeds rules |
|----------|---------------------------|-------------|
| Column data types, partition flag | `COLUMNS` | `SUBOPTIMAL_JOIN_KEYS`, `UNFILTERED_PARTITION` |
| Table type (`EXTERNAL` / `VIEW` / …) | `TABLES` | `NATIVE_CONVERSION` |
| Row counts & byte sizes | `TABLE_STORAGE` | `JOIN_ORDERING` |
| Failed jobs & error reason | `JOBS_BY_PROJECT` | `RESOURCE_FAILURES` |

If no metadata is supplied, metadata-aware rules simply don't fire (the report notes this), so the tool stays useful for pure-SQL linting.

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
