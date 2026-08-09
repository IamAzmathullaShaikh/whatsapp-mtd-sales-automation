# Tools

Every capability is a `Tool` (see `azmath/tools/base.py`): name, description,
parameter schema, default permission, timeout, `run()` that never raises.
Tools are registered in a `ToolRegistry`; the model picks them from schemas
injected into the prompt.

Run `azmath tools list` for the live registry (21 tools), `azmath tools list
--schemas` for full schemas.

## Bundled tools

| Tool | Permission | Purpose |
|---|---|---|
| `fs.list` / `fs.read` / `fs.grep` / `fs.search` / `fs.metadata` | safe | Inspect the workspace |
| `fs.write` / `fs.mkdir` / `fs.move` / `fs.copy` / `fs.delete` | approval | Mutate the workspace |
| `shell.run` | approval | Execute commands; safe patterns (`ls`, `git status`, `pytest`, …) run without approval via `config/permissions.toml` |
| `git.status` / `git.log` / `git.diff` / `git.branch` | safe | Inspect repos |
| `git.clone` / `git.checkout` / `git.push` | approval | Mutate repos |
| `web.search` / `web.fetch` | safe | Network research (stdlib provider; swappable) |
| `python.exec` | approval | Run Python in an isolated subprocess |

All filesystem tools resolve paths inside the workspace root and **reject
`..` escapes** (a security boundary).

## Permission model

Three levels (`azmath/tools/base.py`):

- **safe** — runs without approval (reads, searches, tests).
- **approval** — requires explicit user consent; **denied in non-interactive
  runs**. `approval_mode` in `config/agent.toml`: `prompt` (ask when a TTY),
  `deny`, `allow`.
- **denied** — never runs.

`config/permissions.toml` overrides tool defaults and adds command patterns
for `shell.run` (first match wins):

```toml
[tools]
"fs.write" = "approval"
[shell.patterns]
"^(ls|pwd|echo|cat|git status|python3? -m pytest)" = "safe"
"^(rm|sudo|pacman|git push|git commit)" = "approval"
```

Dry-run mode (`azmath run --dry-run`) shows what a call would do without
executing it — safe for any permission level.

## Adding a tool

```python
from azmath.tools import Permission, Tool

class MyTool(Tool):
    name = "my.nifty"
    description = "Do the nifty thing."
    parameters = {"input": {"type": "string", "description": "…", "required": True}}
    permission = Permission.SAFE

    def run(self, args):
        def fn(a):
            # ... never raise; return str or ToolResult
            return f"nifty result for {a['input']}"
        return self._execute(fn, args)
```

Register it in `azmath/tools/__init__.py::build_default_registry` (or add a
`register_<group>` helper). That's the whole integration — the loop and CLI
pick it up automatically. Future MCP/plugin integrations plug into the same
`ToolRegistry`.
