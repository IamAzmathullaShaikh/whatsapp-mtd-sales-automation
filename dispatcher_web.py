"""
WhatsApp Sales Automation — Linux WhatsApp Web dispatcher (Selenium + Chromium).

Mirrors the interface and return contract of ``dispatcher.process_dispatch_queue``
so ``main.py`` / ``gui.py`` can select the backend via ``DISPATCH_BACKEND``:

    process_dispatch_queue_web(queue, wait_time, tab_close, close_time, cool_down,
                               max_retries, focus_timeout=15, log=None, confirm_ready=None)
        -> (success, failed, skipped)

Instead of launching a native desktop app through a ``whatsapp://`` URI, this
backend drives **WhatsApp Web** in a real browser. Selenium talks to the browser
through the WebDriver protocol (CDP), so:

  * It works on Linux/Wayland — no global mouse/keyboard automation is needed,
    and the browser window does not even need OS-level focus.
  * Send verification is **DOM-level**, strictly stronger than the Windows
    screenshot heuristic: we wait for the chat compose box, type the exact
    message, read the text back and only then press Enter.

The browser login persists across runs via a dedicated user-data-dir profile
(``WEB_USER_DATA_DIR``); the first run asks you to scan the WhatsApp QR code.

Selenium is imported lazily so this module stays import-safe and unit-testable
with a fake driver (see tests/test_dispatcher_web.py).
"""

import os
import time
import logging
import random
from datetime import datetime

from config import SKIP_DUPLICATE_PHONES

# ---------------------------------------------------------------------------
# WhatsApp Web URLs & selectors (current web.whatsapp.com DOM)
# ---------------------------------------------------------------------------
WA_WEB_URL = "https://web.whatsapp.com"
SEND_URL = "https://web.whatsapp.com/send?phone={phone}"

COMPOSE_SEL = "div[data-testid='conversation-compose-box-input']"  # contenteditable message box
CHATLIST_SEL = "header[data-testid='chatlist-header']"             # visible when logged in
QR_SEL = "canvas[aria-label='Scan this QR code']"                  # first-run login screen
INVALID_POPUP_SEL = "div[data-testid='popup-contents']"            # "phone number is invalid" dialog

TYPE_SETTLE_SECONDS = 0.4   # settle time between typing and reading the box back
SCAN_POLL_SECONDS = 3.0     # QR poll interval while waiting for the user to scan


# ---------------------------------------------------------------------------
# Small pure helpers
# ---------------------------------------------------------------------------
def phone_digits(phone):
    """Returns only the digits of a phone (e.g. '+919876543210' -> '919876543210')."""
    return "".join(ch for ch in str(phone) if ch.isdigit())


def compose_text(el):
    """Normalized text currently present inside a compose box element."""
    return " ".join((el.text or "").split())


def message_matches(el, expected):
    """True when the compose box holds the exact message we intend to send."""
    return compose_text(el) == " ".join(expected.split())


# ---------------------------------------------------------------------------
# Driver creation (lazy selenium import — needs a real browser + selenium 4.6+)
# ---------------------------------------------------------------------------
def _create_driver(user_data_dir, headless=False):
    try:
        from selenium import webdriver
    except ImportError as e:  # pragma: no cover - environment check
        raise RuntimeError(
            "The WhatsApp Web dispatcher needs 'selenium'. Install it with:\n"
            "    pip install -r requirements.txt\n"
            "(and have Chromium or Chrome installed on this machine.)"
        ) from e

    options = webdriver.ChromeOptions()
    if user_data_dir:
        options.add_argument(f"--user-data-dir={os.path.abspath(user_data_dir)}")
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-first-run")
    options.add_argument("--disable-dev-shm-usage")
    # Selenium Manager (bundled since selenium 4.6) downloads a matching chromedriver.
    return webdriver.Chrome(options=options)


# ---------------------------------------------------------------------------
# DOM helpers (duck-typed so tests can inject a fake driver)
# ---------------------------------------------------------------------------
def _find(driver, css, timeout):
    """Waits up to `timeout` seconds for the first element matching `css`.
    Returns the element, or None on timeout."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException

    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, css))
        )
    except TimeoutException:
        return None


def _send_keys(el, text):
    from selenium.webdriver.common.keys import Keys

    el.click()
    # Clear anything left in the box (Ctrl+A, then Delete).
    el.send_keys(Keys.CONTROL, "a")
    el.send_keys(Keys.DELETE)
    el.send_keys(text)


def _ensure_logged_in(driver, login_timeout, log=None):
    """Waits until WhatsApp Web is logged in (or the QR code appears for the user
    to scan on first run). Returns True when the app is ready, raises otherwise."""
    from selenium.webdriver.common.by import By

    deadline = time.time() + login_timeout
    logged_in = _find(driver, CHATLIST_SEL, 5)
    qr_hint_printed = False
    while logged_in is None and time.time() < deadline:
        if _find(driver, QR_SEL, SCAN_POLL_SECONDS) is not None and not qr_hint_printed:
            line = "🖼️  First run detected — scan the QR code shown in the browser window with your phone."
            print(line)
            if log:
                log(line)
            qr_hint_printed = True
        logged_in = _find(driver, CHATLIST_SEL, SCAN_POLL_SECONDS)
    if logged_in is None:
        raise RuntimeError(
            f"Not logged in to WhatsApp Web within {login_timeout}s. "
            "Open https://web.whatsapp.com, scan the QR code, and try again."
        )
    return True


def _detect_invalid_number(driver):
    """Returns the popup element when the phone number is rejected, else None."""
    popup = _find(driver, INVALID_POPUP_SEL, 1)
    if popup is None:
        return None
    text = " ".join((popup.text or "").split()).lower()
    if any(k in text for k in ("invalid", "phone number", "not on whatsapp")):
        return popup
    return None


# ---------------------------------------------------------------------------
# Per-contact send with DOM verification
# ---------------------------------------------------------------------------
def _verify_and_send(driver, phone, final_msg, max_retries, focus_timeout):
    """
    Opens the chat for `phone`, types `final_msg`, verifies the text landed in the
    compose box, then presses Enter.

    Returns one of:
      "ok"       — sent (or at least Enter pressed with verified text in the box)
      "invalid"  — WhatsApp rejected the phone number (no retry: deterministic)
      "fail"     — could not verify/send after all retries
    """
    from selenium.common.exceptions import WebDriverException

    for attempt in range(1, max_retries + 1):
        try:
            driver.get(SEND_URL.format(phone=phone))
        except WebDriverException:
            time.sleep(2)
            continue

        # The number is rejected → deterministic failure, no point retrying.
        if _detect_invalid_number(driver) is not None:
            return "invalid"

        box = _find(driver, COMPOSE_SEL, focus_timeout)
        if box is None:
            time.sleep(2)
            continue

        for _ in range(max_retries):
            _send_keys(box, final_msg)
            time.sleep(TYPE_SETTLE_SECONDS)
            if message_matches(box, final_msg):
                box.send_keys("\n")  # Enter sends in WhatsApp Web
                return "ok"
            # Retry typing on a fresh copy of the box (DOM may have re-rendered).
            box = _find(driver, COMPOSE_SEL, 5)
            if box is None:
                break
    return "fail"


# ---------------------------------------------------------------------------
# Public entry point — same contract as dispatcher.process_dispatch_queue
# ---------------------------------------------------------------------------
def process_dispatch_queue_web(queue, wait_time, tab_close, close_time, cool_down,
                               max_retries, focus_timeout=15, log=None, confirm_ready=None):
    """
    Dispatches the queue through WhatsApp Web (Selenium + Chromium).

    log(line)        : optional callback receiving every progress line (plus stdout).
    confirm_ready()  : optional callback replacing the "press ENTER" gate; return True
                       to start sending or False to abort before the first dispatch.

    wait_time / tab_close / close_time are kept for signature parity with
    dispatcher.process_dispatch_queue (callers pass them positionally) but are
    not used by the web backend.
    """
    def emit(line):
        print(line)
        if log:
            log(line)

    def audit(level, msg):
        getattr(logging, level)(msg)
        if log:
            log(msg)

    success, failed, skipped = 0, 0, 0
    total = len(queue)
    seen_phones = set()

    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    today_str = datetime.now().strftime('%Y.%m.%d')
    receipt_log_path = f"{log_dir}/dispatch_receipts_{today_str}.txt"

    logging.basicConfig(
        filename=f"{log_dir}/dispatch_log_{today_str}.log",
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )

    from config import WEB_USER_DATA_DIR, WEB_HEADLESS, WEB_LOGIN_TIMEOUT

    emit(f"🚀 Actionable dispatch queue loaded: {total} items selected for delivery.")
    emit("🌐 Backend: WhatsApp Web (Selenium + Chromium) — opening the browser…")

    driver = _create_driver(WEB_USER_DATA_DIR, headless=WEB_HEADLESS)
    try:
        driver.get(WA_WEB_URL)
        _ensure_logged_in(driver, WEB_LOGIN_TIMEOUT, log=log)
        emit("✅ Logged in to WhatsApp Web.")
    except Exception as e:
        emit(f"❌ Could not prepare WhatsApp Web: {e}")
        try:
            driver.quit()
        except Exception:
            pass
        return success, failed, skipped

    if confirm_ready is not None:
        if not confirm_ready():
            emit("🛑 Dispatch aborted by user before sending began.")
            driver.quit()
            return success, failed, skipped
    else:
        input("👉 Scan the QR code if prompted, then press ENTER to run…")

    try:
        for idx, item in enumerate(queue, start=1):
            name = item["party"]
            phone = item["phone"]
            msg = item["message"]

            if not phone or phone.strip() == "+":
                emit(f"⏩ [{idx}/{total}] Skipping '{name}': Missing valid phone target configuration.")
                skipped += 1
                continue

            if SKIP_DUPLICATE_PHONES:
                if phone in seen_phones:
                    emit(f"⏩ [{idx}/{total}] Skipping '{name}': Phone {phone} already dispatched (SKIP_DUPLICATE_PHONES).")
                    audit("warning", f"SKIP-DUPLICATE | {name} | {phone}")
                    skipped += 1
                    continue
                seen_phones.add(phone)

            hour = datetime.now().hour
            if hour < 12:
                greeting = "☀️ *Good Morning!*"
            elif hour < 16:
                greeting = "📊 *Good Afternoon!*"
            else:
                greeting = "🌙 *Good Evening!*"

            final_msg = f"{greeting}\n\n{msg}"
            digits = phone_digits(phone)

            emit(f"\n[{datetime.now().strftime('%H:%M:%S')}] [{idx}/{total}] Dispatched Target -> {name} ({phone})")

            start = time.time()
            try:
                result = _verify_and_send(driver, digits, final_msg, max_retries, focus_timeout)
            except Exception as e:
                # Parity with dispatcher.py: a per-contact exception (e.g. stale DOM
                # element mid-send) must fail that contact, not abort the whole run.
                audit("warning", f"Web send error for {name}: {e}")
                result = "fail"

            if result == "invalid":
                failed += 1
                audit("error", f"FAILED-INVALID | {name} | {phone} | WhatsApp rejected this number")
                with open(receipt_log_path, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] FAILED | {name} ({phone}) | Invalid number\n")
                emit(f"❌ '{name}': WhatsApp reports the number as invalid.")
            elif result == "ok":
                success += 1
                audit("info", f"SUCCESS | {name} | {phone} | Verified & sent")
                with open(receipt_log_path, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] SENT | {name} ({phone})\n")
                elapsed = time.time() - start
                remaining = total - idx
                actual_cooldown = cool_down + random.randint(1, 3)
                eta = remaining * (elapsed + actual_cooldown)
                emit(f"⏳ Dynamic ETA Remaining: {int(eta // 60)} min {int(eta % 60)} sec")
                if remaining > 0:
                    time.sleep(actual_cooldown)
            else:
                failed += 1
                audit("error", f"FAILED | {name} | {phone} | Could not verify chat open / text landed")
                with open(receipt_log_path, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] FAILED | {name} ({phone}) | Verification failed\n")
                emit(f"❌ Failed permanently after {max_retries} web processing loops.")
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    return success, failed, skipped
