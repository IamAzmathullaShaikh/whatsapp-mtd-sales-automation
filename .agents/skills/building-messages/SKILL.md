---
name: building-messages
description: Use when changing, previewing, or debugging the WhatsApp message text itself — daily report or monthly-target layout, brand lines, signature fallback, balance-block states, or why a sent message looks wrong.
version: 1.0.0
sources:
  - anthropics/skills
  - mattpocock/skills
license: MIT
---

# Building WhatsApp Messages

## The two builders (templates.py)

- `build_whatsapp_message(...)` — the daily report: header (agency), report date, account, brandwise invoiced, brandwise balance, target-speed line, signature.
- `build_monthly_target_message(...)` — the start-of-month target announcement.

Both take `brand_strings` (list of `{label, actual, balance, target}` items), `market_names` (brand code → full display name), and `user_profile`. Brand display names come from `market_names`, never from the raw code.

## Signature fallback

`_build_signature(profile)` renders "Regards," + bold name + designation + bold agency when the profile has any of those fields; with no profile fields it returns `config.MESSAGE_FOOTER`. **Never hardcode a signature block** — that is the exact bug this fallback was introduced to prevent (`MESSAGE_FOOTER` is the config-driven default).

## The three balance-block states

1. `target_completed=True` → "✅ All brand targets fully completed!" + congratulations line.
2. No balance lines (every brand at/over target) → same completed line, no DRR line.
3. Otherwise → the balance lines + "👉 *Target Speed:* Order an average of X Cases daily…" (DRR from `required_drr`).

## Greeting decoration happens at send time

The dispatchers prepend the greeting (`☀️ Good Morning` / `📊 Good Afternoon` / `🌙 Good Evening` by local hour) to each queue message in `dispatcher.py` and `dispatcher_web.py` — **not** in templates.py. Consequence: the GUI preview dialog shows the message exactly as templates.py rendered it, *without* the greeting. Keep the two dispatchers' greeting logic in sync.

## Verifying

- GUI: Run tab → Load File → the preview dialog renders the exact message for each queued account before dispatch.
- Tests: `tests/test_templates.py` covers layout and the signature fallback. Extend it when touching templates.py.

## Common mistakes

- Editing the message body inside a dispatcher instead of templates.py — it would diverge between the two backends.
- Hardcoding the signature instead of falling back to `MESSAGE_FOOTER`.
- Judging the sent message from the preview alone and missing the greeting prefix the dispatcher adds.
