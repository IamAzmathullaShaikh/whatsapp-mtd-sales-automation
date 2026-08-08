# Skill dispatch — {{query}}

User request:

> {{query}}

Top {{top_k}} matching skills from the library index:

{{ranked}}

For each routed skill:

1. Read the normalized entry: `skills/normalized/<source>/<name>/skill.json` (metadata) and `body.md` (full instructions).
2. Follow the skill's instructions; load its bundled scripts/references from the source clone under `skills/sources/` when it calls for them.
3. If no skill scores above zero, say so plainly and answer from general knowledge instead — do not force a skill.

Provenance: `skills/manifests/` pins each source to a repo + commit SHA; `skills/index/index.json` is the full index.
