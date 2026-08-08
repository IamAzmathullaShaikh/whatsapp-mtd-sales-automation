---
name: excel-schema-and-mapping
description: Use when working with the Excel data files, brand column mapping, missing-column errors, or a data-source header rename. Trigger when a brand shows zero sales, a column is not found, or new files do not match the schema.
version: 1.0.0
sources:
  - anthropics/skills (xlsx)
  - MiniMax-AI/skills (minimax-xlsx)
license: MIT
---

# Excel Schema & Column Mapping

## The schema lives in config.py — a rename is a config change, not a code change

| Setting | Default | Meaning |
|---|---|---|
| `SALES_SHEET` | `"DATA"` | sheet holding transactions |
| `SALES_HEADER_ROW` | `4` | 0-indexed header row of the sales dump |
| `COL_DEPOT` | `"Name Of Depot"` | sales: owning depot |
| `COL_SYNDICATE` | `"SYNDICATE NAME"` | sales: group/syndicate |
| `COL_VENDOR` | `"VENDOR_NAME"` | sales: outlet/vendor |
| `COL_PARTY` | `"PARTY"` | master: join key |
| `COL_SEND` / `COL_PRIORITY` / `COL_PHONE` | `"SEND"` / `"PRIORITY"` / `"PHONE"` | master: report opt-in, priority slab, contact |
| `COL_TOTAL` | `"Total"` | sales: volume column |
| `TOTAL_TARGET_COL` | `"TOTAL_TARGET"` | master: overall target |
| `INDIVIDUAL_SYNDICATE` | `"INDIVIDUAL"` | standalone-outlet sentinel — compared case-sensitively |
| `SEND_YES` | `"YES"` | always-report value (case-insensitive) |

## Brand columns

Default convention: target `<CODE>_TARGET` in the master, actual `<CODE>.1` in the sales dump — overridable per brand via `target_col` / `actual_col` in `user_settings.json`.

## Helpers

- `pipeline.detect_column_candidates(df_sales, df_master)` — suggests column dropdowns for the brand dialog.
- `pipeline.validate_brand_columns(settings, df_sales, df_master)` — missing-column report before a run (skips muted brands).
- GUI: the Brands tab offers detected-column Comboboxes; a run with missing columns warns and asks before continuing.

## When a column is renamed upstream

Edit the value in `config.py` (and only that). No pipeline/template changes. For a brand with a custom column, update it in `user_settings.json` or the Brands tab.

## Common mistakes

- Treating `SALES_HEADER_ROW = 4` as 1-based — it is 0-indexed (the 5th row).
- A typo'd brand column silently zeroing a whole brand — run mapping validation before dispatching.
- Expecting case-insensitivity from `INDIVIDUAL_SYNDICATE` — it is compared as-is.
