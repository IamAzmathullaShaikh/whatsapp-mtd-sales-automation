"""Verification engine.

The agent must not simply act and declare success. After the loop ends, the
verifier inspects the trace and runs optional caller-supplied post-checks
(e.g. "the file now exists"). It distinguishes unavailable / failed / not
permitted / not required per the honesty rule.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .observer import Observer


@dataclass
class VerificationResult:
    ok: bool
    issues: list[str] = field(default_factory=list)
    checks: list[str] = field(default_factory=list)

    def summary(self) -> str:
        if self.ok:
            return "verification passed: " + ("; ".join(self.checks) or "no issues found")
        return "verification FAILED:\n- " + "\n- ".join(self.issues)


class Verifier:
    """Generic trace-based verification plus extensible post-checks."""

    def __init__(self, post_checks: list | None = None):
        # post_checks: list of (description, callable() -> bool)
        self.post_checks = post_checks or []

    def verify(self, task: str, observer: Observer, final_answer: str) -> VerificationResult:
        issues: list[str] = []
        checks: list[str] = []
        for call in observer.failed_calls():
            error = call.get("error") or ""
            tool = call.get("tool", "?")
            if "unavailable" in error or "no network" in error or "could not fetch" in error:
                issues.append(f"{tool}: capability unavailable ({error[:120]})")
            elif "not permitted" in error or "denied" in error or "disabled" in error:
                issues.append(f"{tool}: not permitted ({error[:120]})")
            else:
                issues.append(f"{tool}: failed ({error[:160]})")
        if observer.has_tool_use() and not final_answer.strip():
            issues.append("no final answer produced after tool use")
        if not issues and observer.has_tool_use():
            checks.append("all tool calls succeeded")
        for description, fn in self.post_checks:
            outcome = bool(fn())
            checks.append(f"{description}: {'OK' if outcome else 'FAILED'}")
            if not outcome:
                issues.append(f"post-check failed: {description}")
        return VerificationResult(ok=not issues, issues=issues, checks=checks)
