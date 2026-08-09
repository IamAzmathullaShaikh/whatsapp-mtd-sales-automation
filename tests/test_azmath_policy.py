"""M3/M8 — permission policy + approval handling (acceptance I: destructive op blocked)."""

from azmath.tools import ApprovalHandler, Permission, Policy, Tool, decide


class SafeTool(Tool):
    name = "safe.read"
    description = "reads"
    permission = Permission.SAFE

    def run(self, args):
        return "ok"


class WriteTool(Tool):
    name = "fs.write"
    description = "writes"
    permission = Permission.APPROVAL

    def run(self, args):
        return "ok"


class DeniedTool(Tool):
    name = "fs.delete"
    description = "deletes"
    permission = Permission.DENIED

    def run(self, args):
        return "ok"


class ShellTool(Tool):
    name = "shell"
    description = "shell"
    permission = Permission.APPROVAL

    def run(self, args):
        return "ok"


def test_safe_runs_without_approval():
    policy = Policy({})
    allowed, reason, level = decide(SafeTool(), {}, policy, ApprovalHandler("deny"))
    assert allowed and level is Permission.SAFE


def test_approval_denied_noninteractive():
    policy = Policy({})
    allowed, reason, level = decide(WriteTool(), {}, policy, ApprovalHandler("deny"))
    assert not allowed and "approval required" in reason


def test_approval_allowed_in_allow_mode():
    policy = Policy({})
    allowed, _, level = decide(WriteTool(), {}, policy, ApprovalHandler("allow"))
    assert allowed and level is Permission.APPROVAL


def test_approval_prompt_uses_input_fn():
    policy = Policy({})
    answers = []
    approver = ApprovalHandler("prompt", input_fn=lambda p: answers.append(p) or "y")
    allowed, _, _ = decide(WriteTool(), {}, policy, approver)
    assert allowed and answers and "APPROVE" in answers[0]


def test_denied_never_runs():
    policy = Policy({})
    allowed, reason, _ = decide(DeniedTool(), {}, policy, ApprovalHandler("allow"))
    assert not allowed and "denied" in reason


def test_config_overrides_tool_default():
    policy = Policy({"tools": {"safe.read": "denied"}})
    allowed, _, _ = decide(SafeTool(), {}, policy, ApprovalHandler("allow"))
    assert not allowed


def test_shell_patterns_first_match_wins():
    policy = Policy({
        "shell": {"patterns": {
            "^(ls|pwd|echo)": "safe",
            "^(rm|rm -rf)": "approval",
        }}})
    assert policy.level_for(ShellTool(), {"command": "ls -la"}) is Permission.SAFE
    assert policy.level_for(ShellTool(), {"command": "rm -rf /"}) is Permission.APPROVAL
    # unmatched -> tool default
    assert policy.level_for(ShellTool(), {"command": "curl x"}) is Permission.APPROVAL


def test_dry_run_bypasses_approval():
    policy = Policy({})
    allowed, reason, _ = decide(WriteTool(), {}, policy, ApprovalHandler("deny"),
                                dry_run=True)
    assert allowed and "dry-run" in reason
