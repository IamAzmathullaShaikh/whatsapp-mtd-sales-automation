from .base import Permission, Tool, ToolResult
from .policy import ApprovalHandler, Policy, decide
from .registry import ToolRegistry

__all__ = ["ApprovalHandler", "Permission", "Policy", "Tool", "ToolResult",
           "ToolRegistry", "decide"]


def build_default_registry(settings, workspace, web_provider=None) -> ToolRegistry:
    """Register every bundled tool, honoring settings[tools].enabled."""
    from . import fs, git, python_exec, shell, web

    registry = ToolRegistry()
    fs.register_fs(registry, workspace)
    registry.register(shell.RunCommand(workspace, settings.loop.get("tool_timeout", 60)))
    git.register_git(registry, workspace)
    web.register_web(registry, web_provider)
    registry.register(python_exec.ExecPython(workspace))
    # explicit enablement from config: entries are name prefixes ("fs" enables
    # fs.list, fs.read, ...); nothing listed = everything enabled.
    enabled = settings.tools_cfg.get("enabled", [])
    if enabled:
        for name in registry.list():
            if any(name.startswith(prefix) for prefix in enabled):
                registry.enable(name)
    return registry
