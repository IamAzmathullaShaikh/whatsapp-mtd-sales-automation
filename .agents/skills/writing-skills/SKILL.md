---
name: writing-skills
description: Use when creating, revising, or updating a skill in this repository's .agents/skills set, or when deciding whether a repeated procedure should become a skill.
version: 1.0.0
sources:
  - anthropics/skills (skill-creator)
  - obra/superpowers (writing-skills)
  - vercel-labs/skills (find-skills, update flow)
license: MIT
---

# Writing & Updating Skills

## Anatomy

Each skill is `.agents/skills/<name>/SKILL.md` plus optional `scripts/`, `references/`, `assets/`. Flat namespace — one skill per folder, discoverable by name.

## Frontmatter rules (from anthropics + obra)

- Required: `name`, `description`. Optional: `version`, `sources`, `license`.
- `name`: letters, numbers, hyphens only; verb-first reads best (`running-tests`, not `test-helpers`).
- `description` = **when to trigger**, never a workflow summary. Start with "Use when…", include symptoms and searchable terms. A description that summarizes the workflow makes agents skip the body.
- Keep the body under ~500 words; under ~200 for hot-loaded skills. Push heavy reference into `references/` and point to it from the body.

## Good skill vs. not

- Create for: techniques that weren't obvious, recurring workflows, reference knowledge this repo needs.
- Don't create for: one-off solutions, narrative recounts of a single session, anything a regex or a test already enforces.
- Write imperatively, explain the *why*, include one excellent worked example.

## Test before shipping

Run 2–3 realistic prompts against the skill (with and without it) and confirm it changes behavior in the intended direction. Untested skills get skipped by future agents.

## Updating the set

1. Bump `version` in frontmatter; add `sources` entries you leaned on.
2. Run `.agents/skills/scripts/update.sh` to re-fetch the upstream repos this set was learned from and refresh `upstream-manifest.md` — it prints which upstream repos moved.
3. Re-read the manifest, note what changed upstream, and fold worthwhile improvements into these skills.
4. Re-run the test prompts before committing.
