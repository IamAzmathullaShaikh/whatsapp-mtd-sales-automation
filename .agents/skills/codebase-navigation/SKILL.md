---
name: codebase-navigation
description: Use when starting work in this repository, tracing how a request flows from the Excel files to WhatsApp messages, or locating which module holds a given behavior. Trigger on questions like "where does X happen", "how does the data flow", or any task that touches more than one module.
version: 1.0.0
sources:
  - anthropics/skills
  - obra/superpowers
  - mattpocock/skills
license: MIT
---

# Codebase Navigation

## Overview

WhatsApp MTD Sales Automation: reads a monthly sales dump + a party master, computes per-account achievement, builds WhatsApp messages, and sends them through a dispatcher. Everything central that can be configured lives in `config.py`.

## Module map

| Module | Role |
|---|---|
| `main.py` | CLI entry: interactive menus (profile, brands, config), `run_dispatch_engine`, `resolve_dispatcher()` |
| `gui.py` | tkinter desktop app wrapping the same engine (Run / Profile / Brands tabs) |
| `pipeline.py` | Pure engine: load, brand map, casting, aggregation, filters, queue building |
| `dispatcher.py` | Windows desktop dispatcher (pyautogui, `whatsapp://` URIs) |
| `dispatcher_web.py` | Linux WhatsApp Web dispatcher (Selenium + Chromium, DOM-level verification) |
| `config.py` | Default schema names, thresholds, timing, backend selection |
| `companies.py` | Per-company registry (profile, brands, party master, MTD prefix, schema) |
| `schema.py` | Auto-detects MTD/party Excel layout (sheet, header row, column roles) |
| `calculations.py` | Pure math: achievement %, status labels |
| `templates.py` | WhatsApp message builders + signature |
| `dashboard.py` | Territory dashboard export (leaderboards per brand) |
| `utils.py` | Logging setup |
| `tests/` | pytest suite (122 tests) |
| `user_settings.json` | Brand portfolio + profile + filters (gitignored) |

## Data flow

Excel files → `pipeline.load_dataframes` → `build_brand_map` (muted brands dropped) → cast columns → filter parties (depots / filter modes) → `aggregate_actuals` → `build_regular_items` / `build_custom_item` → `templates.build_whatsapp_message` → dispatcher (`process_dispatch_queue*`) → WhatsApp + audit log.

## When NOT to use

Pure questions about a specific Excel file's contents (use `excel-schema-and-mapping`), message wording (templates.py alone), or how to run things (use `running-tests` / `launching-the-gui`).

## Common mistakes

- Guessing where logic lives. Brand *muting* is the chokepoint `build_brand_map` — not the GUI.
- Hardcoding values instead of adding a `config.py` knob.
- Editing `gui.py` and `main.py` separately when the behavior lives in `pipeline.py` — both frontends call the same engine.
