---
name: running-tests
description: Use when verifying a change to this repository, running the test suite, or a test is failing. Also use before claiming work is done, fixed, or passing — evidence before claims.
version: 1.0.0
sources:
  - obra/superpowers (verification-before-completion)
  - google/skills
license: MIT
---

# Running and Verifying Tests

## The commands

```bash
cd ~/Projects/whatsapp-mtd-sales-automation
.venv/bin/python -m pytest                      # full suite (122 tests, ~2s)
.venv/bin/python -m pytest -k mute              # subset by keyword
.venv/bin/python -m pytest tests/test_pipeline.py -q
.venv/bin/python -m py_compile gui.py main.py   # syntax check after big edits
```

`pytest.ini` sets `pythonpath = .` and `testpaths = tests`, so plain `pytest` works from the venv too.

## What the suite covers

- `test_calculations.py` — achievement %, status labels
- `test_templates.py` — message building, signature fallback
- `test_pipeline.py` — brand map, casting, filters, column validation, muted brands
- `test_dispatcher_web.py` — web dispatcher with a fake driver

## The verification gate (from obra/superpowers)

Before claiming "done", "fixed", or "passing":

1. Identify the command that proves the claim.
2. Run it fresh, in this session.
3. Read the full output — exit code and failure count.
4. Only then state the claim, with the evidence.

Rationalizations that fail: "should pass", "the previous run passed", "I'm confident", "it's just a doc change". Any module or test edit warrants a fresh run.

## Common mistakes

- Running bare `python` and hitting the wrong interpreter (use `.venv/bin/python`).
- Skipping the run because the edit was "small" — 122 tests run in about two seconds.
- Trusting an agent's success report without independent output.
