# Skills

A skill is **procedural knowledge** — never model weights. The library holds
133 skills across 8 sources (openai, mattpocock, anthropics, cloudflare,
vercel-labs, supabase, curated). Each request discovers the relevant few and
injects only those, so a 4B model never carries the whole library.

## How discovery works

```
task → router (overlap-coefficient scoring, stdlib) → top-k hits
     → loader (excerpt bodies) → injected into the prompt
```

`azmath skills search "excel schema"` previews routing without a model call.

## Commands

```bash
azmath skills stats     # counts per source
azmath skills list      # all skills
azmath skills search Q  # rank skills for a query
azmath skills sync      # clone/update upstream repos (idempotent)
azmath skills build     # normalize + index + manifests
```

`sync` and `build` reuse the proven `scripts/skilllib` pipeline. `sync` is
idempotent: repeated runs never duplicate skills (sha256-based dedup).

## Adding your own skill

Create `.agents/skills/<name>/SKILL.md` (source `curated/local`):

```markdown
---
name: my-skill
description: Use this skill when ...
version: 1.0.0
---
# Instructions (the body injected into prompts)
```

Then `azmath skills build` to index it. The agent picks it up immediately —
no model rebuild. Follow the conventions of the existing 11 curated skills
(see `.agents/skills/README.md`), and treat the body as executable guidance
(see SECURITY.md).

## Where things live

- `skills/sources/` — git clones (gitignored, refetchable via `sync`)
- `skills/normalized/` — parsed SKILL.md bodies
- `skills/index/index.json` — the routing index
- `skills/manifests/` — per-source + library manifests
- `.agents/skills/` — curated project skills
