# Prompt Templates

| File | Used by | Purpose |
|---|---|---|
| `route.md` | `scripts.skilllib route` | Wraps the routed skill hits for an agent: what to load, in what order, and when to fall back to general knowledge. |
| `skill-use.md` | any agent working with skills | Ground rules for consuming a skill (trigger discipline, progressive disclosure, repo wins on conflict). |

`route.md` is filled by `router.router.render_route` — it replaces `{{query}}`,
`{{top_k}}`, and `{{ranked}}` placeholders.
