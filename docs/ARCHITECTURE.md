# azmath — Architecture

azmath is a **general-purpose autonomous local agent platform**: a small model
surrounded by an extensible runtime (tools, skills, permissions, memory,
verification). The model never "learns" capabilities — the runtime injects the
relevant ones per request.

```
USER
  ↓
AGENT LOOP (core/agent/loop.py)
  ↓ route skills → build prompt → provider.generate → parse
  ├─ tool call? → Policy → Approval → ToolRegistry → execute → observe → repeat
  └─ plain answer? → Verifier → final result
```

## Modules

```
azmath/
├── core/
│   ├── agent/        loop.py (orchestrator) · planner.py (prompt + JSON parsing)
│   │                 executor.py (policy-gated tool execution) · observer.py
│   │                 (trace) · verifier.py (outcome checks)
│   ├── config/       settings.py — TOML + AZMATH_* env overrides (stdlib tomllib)
│   ├── context/      manager.py — prompt sections + budgets (no blind appends)
│   ├── memory/       short_term.py (session) · long_term.py (JSON store) · store.py
│   └── events/       bus.py — structured events, JSONL trace, secret redaction
├── models/           base.py (ModelProvider protocol) · registry.py · ollama.py
├── tools/            base.py (Tool) · registry.py · policy.py (permissions)
│                     fs.py · shell.py · git.py · web.py · python_exec.py
├── skills/           registry.py · loader.py · resolver.py (bridge to router/)
├── runtime.py        dependency-injection factory (CLI + tests build from here)
└── cli.py            azmath CLI
```

## Key design decisions

1. **Provider-agnostic tool calling via a JSON protocol.** The model emits
   `{"tool": "...", "args": {...}}` (or `arguments`) or a plain answer. No
   dependency on Ollama's native function-calling API, so any future provider
   works without runtime changes. `parse_tool_call` accepts both `args` and
   `arguments` spellings (verified live: qwen3:4b emits `arguments`).
2. **The runtime owns termination.** Iteration cap, per-call timeouts, empty-
   response detection, and tool failure isolation live in the loop. A model
   that keeps calling tools is stopped at `max_iterations`, never trusted to
   stop itself.
3. **No hard-coded task branches.** Tools are discovered via `ToolRegistry`
   and chosen by the model from serialized schemas. Adding a capability = new
   Tool + register; nothing in the loop changes.
4. **Skills stay out of weights.** `SkillResolver` routes each request against
   the library index (existing `router/` + 133-skill index) and injects only
   the top-k excerpts. Curated project skills (`.agents/skills/`) are injected
   as `curated/local`.
5. **CPU-first.** stdlib-only platform code, streaming generation, bounded
   context, lazy tool imports, JSON memory store — no vector DB, no GPU.

## The loop in detail

For each iteration:
1. `SkillResolver.resolve(task)` → top-k skill excerpts.
2. `ContextManager.build_prompt(...)` → tools schema + skills + history +
   observations + task (each section capped).
3. `provider.generate(prompt, system)` → text.
4. `parse_tool_call` → if a call: `Policy.level_for` → `ApprovalHandler` →
   `ToolRegistry.execute` → `Observer.record` → loop. If not: final answer.
5. `Verifier.verify(task, trace, answer)` distinguishes **unavailable /
   failed / not permitted / not required**, plus extensible post-checks.

Progress lines describe *actions* ("tool: fs.list ..."), never reasoning.
