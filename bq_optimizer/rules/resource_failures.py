from typing import List
import sqlglot.expressions as exp
from .base import SessionRule, Finding, Severity


class ResourceFailuresRule(SessionRule):
    rule_id = "RESOURCE_FAILURES"
    title = "Job failed due to resource/capacity limits"
    requires_metadata = True

    def analyze_session(self, statements: List[exp.Expression], context) -> List[Finding]:
        if context is None or context.metadata is None:
            return []
        findings: List[Finding] = []
        for job in context.metadata.get_failed_jobs():
            if not job.failed_on_resources:
                continue
            reason = job.error_reason or "resource limit"
            findings.append(Finding(
                rule_id=self.rule_id,
                title=self.title,
                severity=Severity.CRITICAL,
                description=(
                    f"Job '{job.job_id}' failed with '{reason}'"
                    + (f": {job.error_message}" if job.error_message else "")
                    + ". The query was killed for exceeding available compute (slots/memory/shuffle)."
                ),
                recommendation=(
                    "Reduce shuffle and per-stage memory: filter on partition/cluster columns earlier, "
                    "avoid SELECT * and wide cross/self joins, pre-aggregate or materialize large "
                    "intermediate results, and split very large statements. If failures persist under "
                    "a fair query, review slot reservations/capacity for the workload."
                ),
                original_snippet=(job.query[:80] + "...") if job.query else f"job {job.job_id}",
                suggested_snippet="Add partition filters + materialize intermediates; review slot capacity",
            ))
        return findings
