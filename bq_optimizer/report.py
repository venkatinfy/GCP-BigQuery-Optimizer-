"""Text and HTML reporters for BigQuery optimization analysis results."""

from __future__ import annotations

import html as html_mod
from typing import Optional

from .analyzer import AnalysisResult
from .rules.base import Severity


# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------

ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_RED = "\033[31m"
ANSI_YELLOW = "\033[33m"
ANSI_CYAN = "\033[36m"
ANSI_GREEN = "\033[32m"
ANSI_DIM = "\033[2m"


def _severity_color(severity: Severity, no_color: bool) -> str:
    if no_color:
        return ""
    return {
        Severity.CRITICAL: ANSI_RED,
        Severity.WARNING: ANSI_YELLOW,
        Severity.INFO: ANSI_CYAN,
    }.get(severity, "")


# ---------------------------------------------------------------------------
# TextReporter
# ---------------------------------------------------------------------------

class TextReporter:
    """Render an AnalysisResult as a human-readable text report."""

    def __init__(self, no_color: bool = False) -> None:
        self.no_color = no_color

    def _c(self, text: str, color: str) -> str:
        if self.no_color:
            return text
        return f"{color}{text}{ANSI_RESET}"

    def render(self, result: AnalysisResult) -> str:
        lines: list[str] = []
        sep = "=" * 50

        lines.append(self._c(sep, ANSI_BOLD))
        lines.append(self._c("  BigQuery Query Optimizer Report", ANSI_BOLD))
        lines.append(self._c(sep, ANSI_BOLD))
        lines.append("")

        lines.append(self._c("ORIGINAL QUERY:", ANSI_BOLD))
        for sql_line in result.original_sql.splitlines():
            lines.append(f"  {sql_line}")
        lines.append("")

        lines.append(self._c("ANALYSIS SUMMARY:", ANSI_BOLD))
        lines.append(f"  Statements analyzed: {result.statement_count}")
        meta_note = "metadata: supplied (INFORMATION_SCHEMA-aware rules active)" \
            if result.metadata_used else "metadata: none (metadata-aware rules skipped)"
        lines.append(f"  {meta_note}")
        lines.append(f"  Total findings: {result.total_count}")
        crit = self._c(f"Critical: {result.critical_count}", ANSI_RED if not self.no_color else "")
        warn = self._c(f"Warnings: {result.warning_count}", ANSI_YELLOW if not self.no_color else "")
        info = self._c(f"Info: {result.info_count}", ANSI_CYAN if not self.no_color else "")
        lines.append(f"  {crit}  |  {warn}  |  {info}")
        lines.append("")

        if result.findings:
            lines.append(self._c("FINDINGS:", ANSI_BOLD))
            for idx, finding in enumerate(result.findings, 1):
                color = _severity_color(finding.severity, self.no_color)
                header = self._c(
                    f"  [{idx}] {finding.severity.value} - {finding.rule_id}", color
                )
                lines.append(header)
                lines.append(f"      Title: {finding.title}")
                if finding.line_hint:
                    lines.append(f"      Location: {finding.line_hint}")
                lines.append(f"      Description: {finding.description}")
                lines.append(f"      Recommendation: {finding.recommendation}")
                if finding.original_snippet:
                    lines.append(
                        f"      Original:  {self._c(finding.original_snippet, ANSI_DIM)}"
                    )
                if finding.suggested_snippet:
                    lines.append(
                        f"      Suggested: {self._c(finding.suggested_snippet, ANSI_GREEN)}"
                    )
                lines.append("")
        else:
            lines.append(self._c("  No issues found. Query looks good!", ANSI_GREEN))
            lines.append("")

        lines.append(self._c("OPTIMIZED QUERY:", ANSI_BOLD))
        for sql_line in result.rewritten_sql.splitlines():
            lines.append(f"  {sql_line}")
        lines.append("")

        lines.append(self._c(sep, ANSI_BOLD))
        lines.append(self._c("  End of Report", ANSI_BOLD))
        lines.append(self._c(sep, ANSI_BOLD))

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# HTMLReporter
# ---------------------------------------------------------------------------

_HTML_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       background: #f5f7fa; color: #1a1a2e; line-height: 1.6; }
header { background: linear-gradient(135deg, #1a73e8, #0d47a1);
         color: #fff; padding: 24px 32px; }
header h1 { font-size: 1.6rem; }
header p  { opacity: 0.85; font-size: 0.9rem; margin-top: 4px; }
.container { max-width: 960px; margin: 32px auto; padding: 0 16px; }
section { background: #fff; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,.08);
          margin-bottom: 24px; padding: 24px; }
h2 { font-size: 1.1rem; margin-bottom: 12px; color: #1a73e8; border-bottom: 1px solid #e8eaed; padding-bottom: 8px; }
pre { background: #282c34; color: #abb2bf; border-radius: 6px; padding: 16px;
      overflow-x: auto; font-size: 0.85rem; line-height: 1.5; }
.summary-cards { display: flex; gap: 12px; flex-wrap: wrap; }
.card { flex: 1; min-width: 120px; padding: 16px; border-radius: 8px; text-align: center; }
.card .num { font-size: 2rem; font-weight: 700; }
.card .label { font-size: 0.8rem; text-transform: uppercase; opacity: 0.85; }
.card-critical { background: #fce8e6; color: #c5221f; }
.card-warning  { background: #fef3cd; color: #e37400; }
.card-info     { background: #e8f0fe; color: #1a73e8; }
.card-total    { background: #f1f3f4; color: #3c4043; }
.finding { border: 1px solid #e8eaed; border-radius: 6px; margin-bottom: 12px; overflow: hidden; }
.finding-header { padding: 12px 16px; cursor: pointer; display: flex; align-items: center; gap: 12px; }
.finding-header:hover { filter: brightness(0.97); }
.badge { padding: 3px 10px; border-radius: 999px; font-size: 0.75rem; font-weight: 700; }
.badge-CRITICAL { background: #c5221f; color: #fff; }
.badge-WARNING  { background: #e37400; color: #fff; }
.badge-INFO     { background: #1a73e8; color: #fff; }
.finding-title { font-weight: 600; flex: 1; }
.finding-body { padding: 12px 16px; border-top: 1px solid #e8eaed; display: none; }
.finding.open .finding-body { display: block; }
.finding-body p { margin-bottom: 8px; }
.finding-body .label { font-weight: 600; color: #5f6368; font-size: 0.85rem; }
.snippet { font-family: monospace; font-size: 0.85rem; padding: 6px 10px; border-radius: 4px; display: inline-block; }
.snippet-orig { background: #fce8e6; color: #c5221f; }
.snippet-sugg { background: #e6f4ea; color: #1e8e3e; }
.copy-btn { background: #1a73e8; color: #fff; border: none; border-radius: 6px;
            padding: 8px 18px; cursor: pointer; font-size: 0.85rem; margin-bottom: 12px; }
.copy-btn:hover { background: #1557b0; }
footer { text-align: center; color: #9aa0a6; font-size: 0.8rem; padding: 24px; }
"""

_HTML_JS = """
document.querySelectorAll('.finding-header').forEach(function(h) {
  h.addEventListener('click', function() {
    h.closest('.finding').classList.toggle('open');
  });
});
document.getElementById('copy-btn').addEventListener('click', function() {
  var text = document.getElementById('optimized-sql').textContent;
  navigator.clipboard.writeText(text).then(function() {
    document.getElementById('copy-btn').textContent = 'Copied!';
    setTimeout(function() {
      document.getElementById('copy-btn').textContent = 'Copy to clipboard';
    }, 2000);
  });
});
"""


class HTMLReporter:
    """Render an AnalysisResult as a self-contained HTML report."""

    def render(self, result: AnalysisResult) -> str:
        e = html_mod.escape

        findings_html_parts: list[str] = []
        for idx, finding in enumerate(result.findings, 1):
            orig = (
                f'<p><span class="label">Original:</span><br>'
                f'<code class="snippet snippet-orig">{e(finding.original_snippet)}</code></p>'
            ) if finding.original_snippet else ""
            sugg = (
                f'<p><span class="label">Suggested:</span><br>'
                f'<code class="snippet snippet-sugg">{e(finding.suggested_snippet)}</code></p>'
            ) if finding.suggested_snippet else ""
            loc = (
                f'<p><span class="label">Location:</span> {e(finding.line_hint)}</p>'
            ) if finding.line_hint else ""

            findings_html_parts.append(f"""
<div class="finding">
  <div class="finding-header">
    <span class="badge badge-{e(finding.severity.value)}">{e(finding.severity.value)}</span>
    <span class="finding-title">[{idx}] {e(finding.title)}</span>
    <small style="color:#9aa0a6">{e(finding.rule_id)}</small>
  </div>
  <div class="finding-body">
    {loc}
    <p><span class="label">Description:</span> {e(finding.description)}</p>
    <p><span class="label">Recommendation:</span> {e(finding.recommendation)}</p>
    {orig}
    {sugg}
  </div>
</div>""")

        findings_section = "\n".join(findings_html_parts) if findings_html_parts else "<p>No issues found. Query looks good!</p>"

        no_findings_note = "" if result.findings else '<p style="color:#1e8e3e;font-weight:600">✓ No optimization issues detected.</p>'

        html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BigQuery Query Optimizer Report</title>
<style>
{_HTML_CSS}
</style>
</head>
<body>
<header>
  <h1>BigQuery Query Optimizer Report</h1>
  <p>Systematic rule-based SQL analysis</p>
</header>
<div class="container">

  <section>
    <h2>Original Query</h2>
    <pre>{e(result.original_sql)}</pre>
  </section>

  <section>
    <h2>Analysis Summary</h2>
    <p style="color:#5f6368;font-size:0.85rem">
      Statements analyzed: {result.statement_count} &nbsp;|&nbsp;
      {"Metadata supplied — INFORMATION_SCHEMA-aware rules active" if result.metadata_used else "No metadata — metadata-aware rules skipped"}
    </p>
    {no_findings_note}
    <div class="summary-cards">
      <div class="card card-total">
        <div class="num">{result.total_count}</div>
        <div class="label">Total</div>
      </div>
      <div class="card card-critical">
        <div class="num">{result.critical_count}</div>
        <div class="label">Critical</div>
      </div>
      <div class="card card-warning">
        <div class="num">{result.warning_count}</div>
        <div class="label">Warnings</div>
      </div>
      <div class="card card-info">
        <div class="num">{result.info_count}</div>
        <div class="label">Info</div>
      </div>
    </div>
  </section>

  <section>
    <h2>Findings</h2>
    {findings_section}
  </section>

  <section>
    <h2>Optimized Query</h2>
    <button class="copy-btn" id="copy-btn">Copy to clipboard</button>
    <pre id="optimized-sql">{e(result.rewritten_sql)}</pre>
  </section>

</div>
<footer>Generated by bq-optimizer v0.1.0</footer>
<script>
{_HTML_JS}
</script>
</body>
</html>"""
        return html_doc
