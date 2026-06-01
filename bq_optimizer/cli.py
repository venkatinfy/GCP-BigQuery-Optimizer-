"""CLI entry point for bq-optimizer."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from .analyzer import QueryAnalyzer
from .report import TextReporter, HTMLReporter
from .rules.base import Severity
from .metadata.static import StaticMetadataProvider


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bq-optimizer",
        description="Analyze and optimize BigQuery SQL queries.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--query", metavar="TEXT", help="SQL query string to analyze")
    group.add_argument("--file", metavar="PATH", type=Path, help="SQL file to read")
    parser.add_argument(
        "--metadata",
        metavar="PATH",
        type=Path,
        help=(
            "JSON metadata fixture (table types/sizes/columns + failed jobs) modelled on "
            "INFORMATION_SCHEMA. Enables metadata-aware rules such as join keys, native "
            "conversion, join ordering, and resource failures."
        ),
    )
    parser.add_argument(
        "--output-html",
        metavar="PATH",
        type=Path,
        help="Write HTML report to this file",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colors in text output",
    )
    return parser


def _read_sql(args: argparse.Namespace) -> Optional[str]:
    if args.query:
        return args.query
    if args.file:
        try:
            return args.file.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"Error reading file: {exc}", file=sys.stderr)
            return None
    # Try stdin
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return None


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    sql = _read_sql(args)
    if not sql or not sql.strip():
        parser.print_help()
        sys.exit(1)

    metadata = None
    if args.metadata:
        try:
            metadata = StaticMetadataProvider.from_file(args.metadata)
        except (OSError, ValueError) as exc:
            print(f"Error reading metadata file: {exc}", file=sys.stderr)
            sys.exit(1)

    analyzer = QueryAnalyzer(metadata=metadata)
    result = analyzer.analyze(sql)

    if args.format == "json":
        output = {
            "original_sql": result.original_sql,
            "rewritten_sql": result.rewritten_sql,
            "parse_error": result.parse_error,
            "statement_count": result.statement_count,
            "metadata_used": result.metadata_used,
            "summary": {
                "total": result.total_count,
                "critical": result.critical_count,
                "warnings": result.warning_count,
                "info": result.info_count,
            },
            "findings": [
                {
                    "rule_id": f.rule_id,
                    "title": f.title,
                    "severity": f.severity.value,
                    "description": f.description,
                    "recommendation": f.recommendation,
                    "line_hint": f.line_hint,
                    "original_snippet": f.original_snippet,
                    "suggested_snippet": f.suggested_snippet,
                }
                for f in result.findings
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        reporter = TextReporter(no_color=args.no_color)
        print(reporter.render(result))

    if args.output_html:
        html_reporter = HTMLReporter()
        html_content = html_reporter.render(result)
        try:
            args.output_html.write_text(html_content, encoding="utf-8")
            print(f"\nHTML report written to: {args.output_html}", file=sys.stderr)
        except OSError as exc:
            print(f"Error writing HTML report: {exc}", file=sys.stderr)
            sys.exit(1)

    # Exit with non-zero if critical findings
    if result.critical_count > 0:
        sys.exit(2)


if __name__ == "__main__":
    main()
