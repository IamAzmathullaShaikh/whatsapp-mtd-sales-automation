# Skill Library Configuration

This directory holds the skill library's configuration:

| File | Purpose |
|---|---|
| `library.toml` | Sources (upstream skill repos), paths, router weights |

**Note:** this directory intentionally has **no `__init__.py`** and only holds data.
It must never become a Python package — the application's `config.py` module lives
at the repository root, and a `config` package would shadow it. The library reads
this TOML via `scripts/common.py` (`load_library_config`), never via `import config`.

## Sources

`[[sources.repos]]` entries with `enabled = true` are synced by
`python -m scripts.skilllib sync`. Each is cloned (shallow) into
`skills/sources/<owner>/<repo>/`. Flip `enabled` to `true` or pass `--all`
to pull in the rest of the ecosystem repos we studied
(google, obra/superpowers, emilkowalski, MiniMax-AI, slavingia, MengTo,
multica-ai, VoltAgent).
