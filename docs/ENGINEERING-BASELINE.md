# AZMATH AGENT — ENGINEERING BASELINE

Audit date: 2026-08-09 · Repo: `whatsapp-mtd-sales-automation` · Branch: `main`

This is the M0 deliverable: a factual inventory of the machine and the existing
codebase before the agent platform rework. Every number below was measured on
this machine, not estimated.

---

## 1. Machine environment

| Item | Finding |
|---|---|
| OS | CachyOS (Arch-based), Linux 7.1.6, x86_64 |
| CPU | Intel Core i5-1135G7 (Tiger Lake) @ 2.40 GHz, 8 threads |
| RAM | 14 GiB total, ~9.5 GiB available at audit time |
| GPU | Intel Iris Xe (integrated) — **no CUDA, no VRAM** |
| Python | 3.12.13 (project venv at `.venv/`) |
| Ollama | 0.32.6, serving on `http://localhost:11434` |
| Ollama models | `qwen3:4b` (2.5 GB), `azmath-agent:latest` (2.5 GB, custom Modelfile) |
| Git | 2.55.0 |
| Network | Reachable (GitHub API returned HTTP 200) |

**Resource constraints (hard):** CPU-only inference, ~9.5 GiB free RAM, 16K
context is the comfortable ceiling (`num_ctx=32768` was benchmarked earlier and
pushed this machine into swap). Everything in the platform must be lazy,
streaming, and bounded.

---

## 2. What already exists (inventory)

### Skill library (mature, tested)
- `skills/sources/` — git clones of upstream skill repos (gitignored, refetchable)
- `skills/normalized/` — 133 parsed `SKILL.md` → `body.md` + `skill.json` entries
- `skills/index/index.json` — **133 skills across 8 sources**:
  openai/skills (44), mattpocock/skills (35), anthropics/skills (18),
  cloudflare/skills (13), curated/local (11), vercel-labs/agent-skills (9),
  supabase/agent-skills (2), vercel-labs/skills (1)
- `skills/manifests/` — per-source + `library.json` manifests
- `.agents/skills/` — 11 **curated project skills** (dispatch pipeline, GUI,
  web dispatch, running tests, writing skills, …), source `curated/local`

### Router (mature, stdlib-only, pure)
- `router/` — `tokenizer.py` / `scoring.py` (overlap-coefficient ranking with
  name/keywords/description/bigram weights) / `router.py` (`route()`). Fully
  unit-tested. No vector DB — deliberate for a CPU box.

### Agent (functional but single-shot)
- `agent/ollama_client.py` — stdlib REST client: streaming, timeouts,
  `OllamaUnavailable`, UTF-8-safe chunk decode. Proven in production here.
- `agent/solver.py` — route → load top-k skill excerpts → inject into prompt →
  generate. Rolling chat history (`trim_history`), `think="auto"` tiers
  (simple=200-token cap, complex=1600). Returns `(response, used_skills, info)`.
- `agent/modelfile.py` — renders `Modelfile` from `prompts/agent-system.md`
  (the tight, no-narration personality; `azmath-agent` model already built).
- `scripts/skilllib.py` — CLI: `sync/build/route/stats/export/import/ollama/
  agent/chat/modelfile`.

### Project baseline
- **146 tests pass** (`pytest -q`, 3.1s): calculations, templates, pipeline,
  schema, companies, dispatcher_web, skilllib, agent.
- `config/library.toml` — library/router/agent settings + 17 upstream sources.
- `prompts/agent-system.md` — 13-rule personality (no chain-of-thought output).
- Requirements: pandas, numpy, openpyxl, questionary, pyautogui, selenium
  (needed by the MTD dispatch app, not by the agent platform).

---

## 3. Gap analysis vs the target architecture

| Capability | Status | Note |
|---|---|---|
| Model provider abstraction | ❌ | `solver` calls Ollama directly; no `ModelProvider` interface, no registry |
| Tool system | ❌ | No `Tool` abstraction, no registry, no schemas, no permission metadata |
| Agent loop (iterate → observe → re-evaluate → verify) | ❌ | `solve()` is single-shot text generation |
| Verification engine | ❌ | Nothing checks outcomes; skills say "verify" but nothing enforces it |
| Permission system | ❌ | No classification of safe vs approval operations |
| Context management | ◐ | `trim_history` only; no budgets, compression, or priority retention |
| Memory | ❌ | No short/long-term store |
| Observability | ❌ | `print`-based; no task/session IDs, no structured logs |
| Generic CLI (`azmath run/tools/models/doctor/config`) | ❌ | `skilllib` exists but is skills-library-focused |
| Skills: discovery/ingest/index/router | ✅ | Mature; will be reused via a bridge, not rewritten |
| Skills: validation on custom creation | ◐ | Name/source safety exists; no content-validation gate for custom skills |
| Config | ◐ | TOML exists; no env overrides, no permissions config |
| Security (prompt-injection, trust metadata) | ❌ | Not addressed yet |

---

## 4. Design decisions for the rework

1. **New `azmath/` package, existing subsystems preserved.** The target tree
   is instantiated as a top-level `azmath/` package (core/, models/, tools/,
   skills/, context/, memory/, permissions/, events/, config/). The mature
   `router/`, `skills/` data, and `prompts/agent-system.md` are **reused
   through adapters**, not copied or rewritten.
2. **Provider-agnostic tool calling via a JSON protocol**, not Ollama's native
   function-calling API. The model emits `{"tool": "...", "args": {...}}` or a
   plain answer; the runtime parses, executes, observes, and loops. Works on
   qwen3:4b today and on any future provider without runtime changes.
3. **Prompt-driven tool selection.** Tool schemas (name, description, params,
   permission) are serialized into the prompt from the registry. No
   `if user_mentions_x:` branches anywhere — the model chooses.
4. **Runtime owns termination.** Iteration cap, per-call timeout, total budget,
   and cancellation live in the loop, not in the model.
5. **CPU-first.** Lazy tool imports, streaming, bounded context, stdlib-first.
   No vector DB; hybrid keyword routing already fits the machine.

---

## 5. Milestone plan (from the master prompt)

| # | Milestone | Delivered in this rework |
|---|---|---|
| M0 | Audit + baseline | ✅ this document |
| M1 | Core configuration | `azmath/core/config/settings.py`, `config/agent.toml`, `config/permissions.yaml` |
| M2 | Model provider abstraction | `azmath/models/` base + registry + OllamaProvider |
| M3 | Tool abstraction + registry | `azmath/tools/` base + registry + policy + fs/shell/git/web/python |
| M4 | Agent execution loop | `azmath/core/agent/` planner/executor/observer/verifier/loop |
| M5 | Context management | `azmath/core/context/` budget + trimming |
| M6 | Memory | `azmath/core/memory/` short-term + long-term JSON store |
| M7 | Verification engine | verifier in the loop + explicit verify step |
| M8 | Permission system | `azmath/tools/policy.py` + `config/permissions.yaml` + approval handler |
| M9 | Skill system bridge | `azmath/skills/` loader/registry/resolver over existing index |
| M10 | Skill ingestion | reuse `scripts.skilllib sync/build` (idempotent, already tested) |
| M11 | Skill retrieval/router | reuse `router/` (already tested) |
| M12 | Observability | `azmath/core/events/` + structured logging, no secrets |
| M13 | CLI | `azmath` entry point + `python -m azmath` |
| M14 | Security hardening | policy defaults, untrusted-content rules, capability honesty |
| M15 | Testing | unit + integration + acceptance (incl. the 7 required scenarios) |
| M16 | Documentation | ARCHITECTURE / TOOLS / CONFIGURATION / SECURITY / SKILLS / TROUBLESHOOTING / DEVELOPMENT |

Milestones marked ✅/existing are reused without rewrite. The rework delivers
M1–M9, M12–M16 as working, tested code (see acceptance criteria below).

---

## 6. Acceptance criteria targeted by this rework

A. `hello` → direct answer, **zero** tool calls.
B. "Inspect my project" → filesystem tools autonomously discovered and used.
C. "Fix the failing tests" → inspect → modify → test → diagnose → retest → verify.
D. "Research this topic" → web tools when available.
E. "Analyse this GitHub repository" → network/git tooling (URL is just a tool input).
F. "Analyze this PDF" → routes to document capabilities; honest if unavailable.
G. "Create an Excel report" → filesystem + spreadsheet tooling + verification.
H. Multi-skill tasks → dynamic discovery + composition.
I. Destructive op → permission system blocks / requests approval.
J. External skills sync without rebuilding the model (already true via `skilllib sync`).

---

## 7. Baseline test evidence

```
146 passed, 41 warnings in 3.13s
```

Run on this machine before any rework code was written.
