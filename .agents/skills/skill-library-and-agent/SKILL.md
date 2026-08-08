---
name: skill-library-and-agent
description: Use when working with the skill library subsystem — skills/ data layout, the router, the skilllib CLI (sync/build/route/stats/export/import/ollama/agent/chat), the local Ollama agent, or adding/exporting skills.
version: 1.0.0
sources:
  - vercel-labs/skills (find-skills, update flow)
  - anthropics/skills
license: MIT
---

# Skill Library & Local Agent

## Layout

```
skills/            sources/ (gitignored clones) · normalized/ · index/ · manifests/
router/            stdlib-only tokenizer + scorer + route()
scripts/           skilllib CLI: sync · build · route · stats · export · import · ollama · agent · chat · modelfile
agent/             ollama_client (streaming REST) · solver (route→inject→generate) · modelfile
config/            library.toml — sources, paths, router weights, [agent] knobs (DATA-ONLY: no __init__.py, must never shadow config.py)
prompts/           route.md · skill-use.md · agent-system.md
```

## The pipeline

`skilllib sync` shallow-clones the `enabled = true` repos in `config/library.toml` → `build` normalizes each SKILL.md (frontmatter → metadata, sha256 hash, names sanitized to `[a-z0-9-]`, duplicates disambiguated), writes `skills/normalized/`, then builds `skills/index/index.json` and the manifests. **Curated project skills** (`.agents/skills/<name>/SKILL.md`) are indexed too, with `source: "curated/local"` — `build` must be re-run after adding one.

## Router & agent flow

`route(query, index, top_k)` scores name/description/keywords/bigrams; hits feed `agent.solver.solve()` which excerpts each skill body (curated ones read from `.agents/skills/`), composes them with the system personality (`prompts/agent-system.md`) and the task, then calls Ollama — streaming, `max_tokens`-capped. `skilllib chat` is a REPL that re-routes every turn and keeps the last `max_history_turns` exchanges.

## Export / import

`skilllib export` → `export/skills-bundle.json` (self-contained: curated + library + index + manifests) and `export/skills-prompt.md` (for handing to another model). `skilllib import bundle.json` restores everything offline with zero pip installs (PyYAML is lazily imported); `build` afterwards regenerates identical index/manifests from the restored tree when no source clones exist. See `skills-migration.md`.

## Common mistakes

- Editing `config/` — it's data-only by design; adding `__init__.py` would shadow the app's `config.py`.
- Adding a curated skill without re-running `build` — it won't appear in the index or route.
- Regenerating export artifacts after changes — the bundle is a snapshot; re-export to keep it current.
- Testing the agent with a real model when a stub suffices — `tests/test_agent.py` runs a stub Ollama server; live calls take minutes on CPU.
