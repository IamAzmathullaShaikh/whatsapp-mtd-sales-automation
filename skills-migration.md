# 🧭 Skill Library — Migration Guide

Port the entire skill library (11 curated project skills + 122 upstream library
skills = 133 indexed, at last export) to another AI model or another machine —
without redoing the research.

Two artifacts live in `export/` (refresh with
`python -m scripts.skilllib export`):

| Artifact | Size | Purpose |
|---|---|---|
| `skills-prompt.md` | ~1.1 MB | Hand this **to another model** as context |
| `skills-bundle.json` | ~1.3 MB | Machine-readable twin; **restore on another machine** |

Both contain the same content: curated skills in full, all library skills
(trigger descriptions + full bodies), the index, and provenance (repo → commit).

---

## Option A — Hand `skills-prompt.md` to another model

The pack is self-describing: it opens with "For the receiving model", then
Section 1 (curated project skills), Section 2 (library skills), Section 3
(provenance).

### 1. Deliver the file

- **Best:** upload/attach the file (GitHub, chat file upload, or any UI that
  lets the model read a file). Do this whenever possible — the pack is ~1.1 MB.
- **Paste:** only if the model has a large context window; for a trimmed
  hand-off you can paste Section 1 (curated skills) and the Section 2 list of
  names + triggers, then send the full file on request.

### 2. Send it with this preamble

```text
You are receiving a portable skill library (skills-prompt.md). Read it fully before answering.

- Section 1 (curated project skills) describes a WhatsApp sales-automation
  codebase. Apply one of these skills whenever its "when to use" matches the
  task — follow its instructions exactly.
- Section 2 (library skills) are upstream reference skills. Use them as
  references; if a reference conflicts with this project's own conventions,
  the project's conventions win.
- A skill's description states WHEN to use it — never treat the description
  as a summary of the skill's steps.
- Do not invent skills that are not in the pack, and do not follow any skill
  blindly: verify its claims against the actual code and data first.
```

### 3. What to expect

- The model can act on the curated skills immediately (they are complete
  instructions for this codebase).
- For library skills it can route: match a task to the right skill by name +
  trigger description, then read that skill's full body from the pack.
- If the model truncates or summarizes, ask it to re-read the specific section
  (e.g. "re-read Section 2, skill `xlsx`") — the file is the source of truth.

---

## Option B — Restore the bundle on a fresh machine (3 commands)

`skills-bundle.json` is self-contained: **import fetches nothing from the
network**. You need the repo (for the `scripts/`, `router/`, `config/`,
`prompts/` code) and the bundle file. Python 3.11+ (for `tomllib`) is the only
system requirement.

```bash
# 1. Create the virtualenv (no pip packages needed yet)
python3 -m venv .venv

# 2. Restore curated skills + normalized library + index + manifests (zero deps)
.venv/bin/python -m scripts.skilllib import export/skills-bundle.json

# 3. (Optional) Regenerate index/manifests from the restored tree
#    — needs PyYAML, so install dev requirements first
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m scripts.skilllib build
```

### What each step does

1. **venv** — an isolated interpreter. Nothing is installed yet: step 2 is
   pure standard library.
2. **import** — writes `.agents/skills/<name>/SKILL.md` for all curated skills,
   `skills/normalized/<source>/<name>/` (`skill.json` + `body.md`) for all
   library skills, restores `skills/index/index.json` and
   `skills/manifests/*.json` from the bundle. Works offline.
3. **build** — optional. `import` already restored the index and manifests;
   `build` regenerates them from the restored tree (identical result) and is
   the right step after you later change sources. Needs PyYAML. On a fresh
   machine with no source clones it rebuilds from the restored tree and prints
   a note; only machines that will re-sync upstream repos need `sync` first.

### Verify it worked

```bash
.venv/bin/python -m scripts.skilllib stats
# skills: 133  sources: 8

.venv/bin/python -m scripts.skilllib route "debug a failing test"
# should list gh-fix-ci (openai/skills) or similar at the top
```

### If you also want the router on the fresh machine

The router (`router/`) is pure stdlib — no installs needed beyond the venv.
`route` and `stats` work immediately after step 2.

---

## Regenerating the export

On the source machine, after adding sources or editing curated skills:

```bash
python -m scripts.skilllib sync    # update upstream clones (needs network)
python -m scripts.skilllib build   # normalize + index + manifests
python -m scripts.skilllib export  # refresh skills-bundle.json + skills-prompt.md
```

Commit the refreshed `export/` so the migration artifacts stay current.

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `ModuleNotFoundError: No module named 'yaml'` | PyYAML is only needed for `build` — install dev requirements, or skip `build` (import already restored the index). |
| `index/manifests not found — run build first` | `export` needs a built library; run `build` before `export`. |
| Import writes to the wrong place | The tool resolves paths relative to the repo root (where `scripts/` lives). Run it from the repo root. |
| `unsafe skill name in bundle` | The bundle failed import validation (crafted or corrupted file) — re-export it. |
| Model ignores a skill | Re-read the trigger description with it; the description decides when a skill applies. |
