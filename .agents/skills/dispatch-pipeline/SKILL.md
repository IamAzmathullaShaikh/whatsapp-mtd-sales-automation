---
name: dispatch-pipeline
description: Use when changing dispatch behavior, tracing how a message is built and sent, or debugging why accounts were or were not messaged. Trigger on brand, filter, or dispatcher questions that reach beyond one module.
version: 1.0.0
sources:
  - anthropics/skills
  - mattpocock/skills
license: MIT
---

# Dispatch Pipeline

## End to end

1. `pipeline.load_dataframes` reads the sales dump + party master.
2. `build_brand_map(settings)` returns the enabled brands — the mute chokepoint. It feeds `sales_brands`, `target_cols`, `market_names`, so muted brands vanish from everything downstream (aggregation, messages, dashboard).
3. `cast_sales_columns` / `cast_target_columns` coerce numeric columns; a missing brand column would silently become 0, so `validate_brand_columns` (skips muted brands) flags missing columns before casting.
4. Parties are filtered: depot checkboxes, then one filter mode — All, Priority, Groups, Custom, or Below Achievement % (`filter_parties_by_achievement`, strict `<`, threshold `ELIGIBILITY_MAX_ACH_PCT`).
5. `aggregate_actuals` → `build_regular_items` / `build_custom_item` → `templates.build_whatsapp_message` (signature falls back to `MESSAGE_FOOTER`).
6. `resolve_dispatcher()` (in `main.py`, used by both frontends) picks the backend: `auto` → Windows desktop, Linux web. Desktop: `dispatcher.process_dispatch_queue` (pyautogui, `whatsapp://` URIs). Web: `dispatcher_web.process_dispatch_queue_web` (Selenium, DOM-verified send, invalid-number popup detection).
7. Audit: log lines + `logs/`; missing contacts exported via `export_missing_contacts`.

## Behavior knobs (config.py)

`TEST_MODE` / `TEST_LIMIT` (cap the queue), `SKIP_DUPLICATE_PHONES`, `COOL_DOWN`, `MAX_RETRIES`, `FOCUS_TIMEOUT`, `WAIT_TIME`, `ELIGIBILITY_MAX_ACH_PCT`, `ELIGIBILITY_MIN_BALANCE`, `DISPATCH_BACKEND`, `WEB_USER_DATA_DIR`, `WEB_HEADLESS`, `WEB_LOGIN_TIMEOUT`.

## Common mistakes

- Adding a filter branch in only one frontend — shared logic goes in `pipeline.py`; both `gui.py` and `main.py` call the engine.
- Forgetting muted-brand semantics when touching `build_brand_map` or `validate_brand_columns`.
- Hardcoding pacing thresholds — they live in `config.py` (`ELIGIBILITY_*`).
- Changing a dispatcher's return contract — `process_dispatch_queue` and `process_dispatch_queue_web` must keep identical signatures and `(sent, failed, invalid)` returns for swap compatibility.
