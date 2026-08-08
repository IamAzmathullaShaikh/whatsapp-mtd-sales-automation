---
name: web-dispatch
description: Use when working with the Linux WhatsApp Web dispatch backend — dispatcher_web.py, Selenium/Chromium setup, QR-code login, DOM-verified sending, invalid-number popups, or choosing DISPATCH_BACKEND.
version: 1.0.0
sources:
  - anthropics/skills
  - mattpocock/skills
license: MIT
---

# WhatsApp Web Dispatch (Linux)

## What it is

`dispatcher_web.process_dispatch_queue_web(queue, wait_time, tab_close, close_time, cool_down, max_retries, focus_timeout=15, log=None, confirm_ready=None)` drives **WhatsApp Web** in a real Chromium via Selenium. It mirrors `dispatcher.process_dispatch_queue`'s signature and `(success, failed, skipped)` return contract, so `resolve_dispatcher()` in main.py swaps backends without touching callers.

It works on Wayland with **no OS-level focus** — unlike the Windows desktop backend, no pyautogui screen automation. Send verification is **DOM-level**: wait for the compose box, type the message, read it back, and only press Enter if it matches exactly.

## Setup (this machine)

`setup_linux.sh` is the reproducible path: system `chromium tk uv` (pacman), a Python 3.12 linked to system Tk (fonts — see `launching-the-gui`), then `uv venv` + requirements. Selenium is in requirements and Selenium Manager auto-downloads chromedriver. Lazy-imported, so the module unit-tests with a fake driver (`tests/test_dispatcher_web.py`).

## Login & first run

Login persists in the dedicated profile at `WEB_USER_DATA_DIR` (config.py). First run opens web.whatsapp.com on the QR screen (`canvas[aria-label='Scan this QR code']`) and waits up to `WEB_LOGIN_TIMEOUT`; after scanning, `confirm_ready()` (GUI) or Enter (CLI) gates the run. If the QR never resolves, the run aborts cleanly before sending anything.

## Send loop semantics

- Missing/blank phones are `skipped`, not failed.
- `SKIP_DUPLICATE_PHONES` dedupes within the run (second occurrence skipped + audited).
- Invalid numbers raise a WhatsApp popup → that contact is `failed`, logged `FAILED-INVALID`, appended to `logs/dispatch_receipts_<date>.txt`; the run continues.
- Per-contact exceptions fail just that contact (parity with the desktop backend).
- `wait_time`/`tab_close`/`close_time` are accepted for signature parity but unused.

## Common mistakes

- Editing only `dispatcher.py` when both backends must stay behavior- and contract-compatible.
- Forgetting the QR/login gate when testing in headless mode (`WEB_HEADLESS`).
- Assuming a screenshot-based check exists here — verification is DOM-level (`message_matches`), which is stronger; don't "port" pyautogui logic into this backend.
