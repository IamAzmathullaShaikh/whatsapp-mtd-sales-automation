# Security

azmath is a general-purpose agent, which means it must be **safe by default,
honest about its limits, and distrustful of content it reads**.

## Permission boundaries

- **Read is free, write needs consent.** Reads/searches/tests are `safe`;
  writes, deletes, pushes, clones, arbitrary shell, and Python execution are
  `approval` — blocked in non-interactive runs unless explicitly allowed
  (`AZMATH_APPROVAL_MODE=allow`).
- **Shell commands are pattern-gated.** `config/permissions.toml` narrows
  `shell.run` (safe patterns like `ls`/`pytest` vs destructive ones). First
  match wins.
- **Dry-run is always safe.** `azmath run --dry-run` executes nothing but
  shows what would happen.
- **The workspace is a boundary.** Filesystem tools resolve paths against the
  workspace root and reject `..` escapes. Web fetch rejects non-http(s) URLs.

## Untrusted content

Skill bodies, web pages, files, tool output, and generated code are all
**data, never instructions**. The system prompt enforces this (and the
observations section is labelled as data). The runtime never parses
instructions out of external content — only the model's own output is treated
as a tool call.

## Honesty (no fake capabilities)

The runtime and the system prompt distinguish:
**unavailable** (e.g. network down → `web.search` fails with a clear reason),
**failed** (tool error), **not permitted** (policy denial), **not required**.
An empty model response is reported as an error, never as completion. The
verifier flags denied/failed calls in the final summary.

## Secrets

- Tool call args that look sensitive (tokens, keys, passwords, write content)
  are redacted in the event trace (`azmath/core/events/bus.py`).
- Logging never emits `AZMATH_*` env values, remote credentials, or model
  API keys.

## Trusting new skills

Skills are executable guidance. Treat newly created custom skills
(`.agents/skills/<name>/SKILL.md`) as untrusted until reviewed — their bodies
are injected into prompts verbatim. Name/source validation already exists in
the import pipeline (`scripts/common.py`); content review is on you.
