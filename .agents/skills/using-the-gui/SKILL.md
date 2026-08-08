---
name: using-the-gui
description: Use when operating the desktop GUI itself — where each setting lives in the window, how the Run/Profile/Brands tabs map to user_settings.json, filter modes, depot selection, or the preview dialog. For launching/troubleshooting the window instead, see launching-the-gui.
version: 1.0.0
sources:
  - google/skills
  - anthropics/skills
license: MIT
---

# Using the GUI (gui.py)

Three tabs + a live log pane. The window is a thin frontend over `pipeline.py` — every setting it edits is persisted to `user_settings.json`.

## Run tab

1. **SALES FILE** — combobox of detected files + Browse… → **Load File** populates depots and the brand/party dropdowns. Status label shows the loaded file + row counts.
2. **REPORT TYPE** — Daily Sales Progress Report or Start-of-Month Target Announcement.
3. **DEPOTS TO PROCESS** — checkbox list with Select All / Clear; the count label updates.
4. **FILTER STRATEGY** — exactly one of five modes (radio): All Eligible, Priority slab (A/B/C), Below Achievement % (threshold combobox, default from `ELIGIBILITY_MAX_ACH_PCT`), Individual Groups, or Custom Consolidation. The sub-widgets live in a fixed frame so switching modes never reorders the tab.
5. **▶ START DISPATCH** — validates (a brand must be enabled; columns must exist), then shows the **preview dialog** (queued accounts left, exact message right). Cancel aborts before anything is sent.

## Profile tab

Executive Name / Designation / Agency → saved to `settings["profile"]`, used in the message header and signature. Save with the button; there is no auto-save.

## Brands tab

Listbox of the portfolio: ✅ enabled / 🔕 muted. **➕ Add / ✏️ Edit** open the brand dialog (code, display name, target column, actual column — Comboboxes are pre-filled via `pipeline.detect_column_candidates`). **🔕 Mute/Unmute** flips `enabled` in-place; muted brands stay in the portfolio but are excluded from every dispatch, aggregation, and column check.

## Settings mapping

`user_settings.json` = `{"profile": {name, designation, agency}, "brands": {CODE: {name, target_col, actual_col, enabled}}}`. Old string-valued brands are migrated automatically on load. Editing the JSON by hand is supported; the GUI rereads it on next launch.

## Common mistakes

- Looking for GUI behavior in the wrong layer — tabs only set settings and call `pipeline`; all logic (filters, brand map, column validation) lives in pipeline.py.
- Muting the last enabled brand — dispatch refuses to start with a clear error; unmute one in the Brands tab.
- Expecting auto-save in the Profile tab — click Save Profile.
