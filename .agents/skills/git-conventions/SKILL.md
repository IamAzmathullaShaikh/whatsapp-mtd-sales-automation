---
name: git-conventions
description: Use when committing, staging, reviewing diffs, or preparing a push for this repository. Trigger on any git workflow question for this repo.
version: 1.0.0
sources:
  - obra/superpowers
  - multica-ai/andrej-karpathy-skills (surgical changes)
license: MIT
---

# Git Conventions

## Commit messages

Conventional commits, lowercase, no scope:

- `feat:` — new capability
- `fix:` — bug fix
- `docs:` — README / documentation
- `chore:` — housekeeping, gitignore
- `build:` — tooling, line-ending / config files

Example: `feat: implement per-brand mute toggle for dispatch`.

When an agent creates the commit, the message ends with the `Generated with Codebuff 🤖` / `Co-Authored-By: Codebuff <noreply@codebuff.com>` footer.

## Rules of the road

- Inspect `git status` and the current branch before any consequential operation — this is a shared checkout; other threads may edit files or switch branches.
- Stage only files relevant to the current change. Never broad-stage (`git add -A`) — it can sweep in someone else's work or the `.freebuff/` app data.
- Do not push unless the user asks.
- README.md is the source of truth for documented behavior — update it when user-facing behavior changes.
- Surgical changes: touch only what the request needs; don't "improve" adjacent code (karpathy-guidelines).

## What's gitignored (do not commit)

`user_settings.json`, `*.xlsx` / `*.csv` except the two template files, `.whatsapp_web_profile/` (holds the WhatsApp login session), `.freebuff/`, `logs/`, `exports/`, `.venv/`, `custom_groups.json`.

## Common mistakes

- Committing `.freebuff/` or the browser profile — the login session leaks.
- Rewriting history on a shared branch.
- Claiming a push succeeded without checking the remote result.
