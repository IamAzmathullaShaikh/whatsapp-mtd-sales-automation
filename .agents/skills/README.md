# Project Skills

Skills authored for this repository, learned from the public skills ecosystem:

- [anthropics/skills](https://github.com/anthropics/skills) — skill anatomy, progressive disclosure, evaluation loop
- [obra/superpowers](https://github.com/obra/superpowers) — description = trigger-only, verification before completion, TDD-for-skills
- [mattpocock/skills](https://github.com/mattpocock/skills) — engineering workflows, two-axis review
- [google/skills](https://github.com/google/skills) — frontmatter richness, onboarding-entrypoint pattern
- [vercel-labs/skills](https://github.com/vercel-labs/skills) — the `npx skills` discover/update flow
- [MiniMax-AI/skills](https://github.com/MiniMax-AI/skills) — document-skill patterns (xlsx/pdf/docx)
- [emilkowalski/skills](https://github.com/emilkowalski/skills) — vocabulary + review-loop teaching
- [slavingia/skills](https://github.com/slavingia/skills) — lean MVP framing
- [MengTo/Skills](https://github.com/MengTo/Skills) — reference-heavy aesthetic recipes
- [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills) — simplicity, surgical changes
- [VoltAgent/awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills) — community skill ecosystem map

## The set

| Skill | Use when | Version |
|---|---|---|
| `codebase-navigation` | Starting work, tracing data flow, locating where a behavior lives | 1.0.0 |
| `running-tests` | Verifying a change, running the suite, claiming work is done | 1.0.0 |
| `launching-the-gui` | Launching/relaunching the desktop GUI, tiny-text or startup trouble | 1.0.0 |
| `dispatch-pipeline` | Changing dispatch behavior, tracing message build/send, why accounts were missed | 1.0.0 |
| `excel-schema-and-mapping` | Excel schema, brand column mapping, missing-column errors, header renames | 1.0.0 |
| `building-messages` | Message text itself: template layout, signature fallback, balance-block states, greeting | 1.0.0 |
| `web-dispatch` | Linux WhatsApp Web backend: dispatcher_web.py, Selenium/QR login, DOM-verified send | 1.0.0 |
| `using-the-gui` | Operating the window: tabs, filter modes, preview dialog, settings mapping | 1.0.0 |
| `skill-library-and-agent` | The skills/ router + skilllib CLI + local Ollama agent subsystem | 1.0.0 |
| `git-conventions` | Committing, staging, reviewing, pushing | 1.0.0 |
| `writing-skills` | Creating/revising skills in this set | 1.0.0 |

## Updating the set

The set is versioned and upstream-tracked. To refresh:

```bash
.agents/skills/scripts/update.sh
```

It shallow-clones the upstream repos into `.agents/skills/.upstream/` (gitignored), records their current commit SHAs and skill counts in `upstream-manifest.md`, and prints a drift report. When an upstream repo moves, review its changes and fold improvements into the relevant skills per `writing-skills`, bumping each skill's `version`.

## Conventions

- Each skill: `.agents/skills/<name>/SKILL.md` with YAML frontmatter (`name`, `description`, `version`, `sources`, `license`).
- `description` states **when to trigger** — never a summary of the skill's steps.
- Bodies stay under ~500 words; heavy reference goes in `references/`.
