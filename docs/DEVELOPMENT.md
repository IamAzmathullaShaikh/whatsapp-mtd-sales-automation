# Development

## Running the tests

```bash
.venv/bin/python -m pytest -q            # full suite (215 tests)
.venv/bin/python -m pytest tests/test_azmath_loop.py -q   # one subsystem
```

The platform tests are offline — they use a `StubProvider` (scripted model
responses), real temp workspaces, and fake web providers. No Ollama needed.

## Layout & conventions

- New platform code goes under `azmath/` (stdlib-first; the dispatch app's
  pandas/selenium dependencies must not leak into the agent runtime).
- Interfaces over implementations: `ModelProvider` protocol, `Tool` base,
  `WebProvider` protocol, replaceable memory backend.
- Tools never raise; failures become `ToolResult(ok=False)`.
- No global mutable state; build everything through `build_runtime()` (DI).
- No circular imports: `azmath/core/*` must not import `azmath/cli.py`.

## Adding a model provider

1. Implement `ModelProvider` (name, `health`, `generate`, `metadata`) in
   `azmath/models/<name>.py`.
2. Register it in `azmath/runtime.py::build_runtime`.
3. Set `provider = "<name>"` in `config/agent.toml` (or `AZMATH_MODEL_PROVIDER`).
   The loop, tools, permissions, and CLI change nothing.

## Adding a tool

See TOOLS.md — subclass `Tool`, register it, done. The model discovers it via
the schema in the prompt; add a permission in `config/permissions.toml` if
needed.

## Adding a skill

See SKILLS.md — drop a SKILL.md in `.agents/skills/`, run
`azmath skills build`. Follow the existing curated skills' conventions and
keep bodies < 500 words.

## Testing checklist for new subsystems

- Unit tests for pure logic (parsing, policy, budgets).
- One integration test through the loop with a stub provider.
- Update `tests/test_azmath_*.py`, keep the full suite green, and run
  `azmath doctor` before finishing.
