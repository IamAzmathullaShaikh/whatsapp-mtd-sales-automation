import os
import time
import logging
import random
from datetime import datetime
from urllib.parse import quote
import numpy as np

# pyautogui needs an X11 session (and on Windows is the desktop-automation engine).
# On Linux/Wayland the import fails (mouseinfo cannot connect to a display), but this
# module must stay importable so main.py/gui.py can load and pick the web backend.
# The verification helpers below already degrade to None when pyautogui is missing.
try:
    import pyautogui
except Exception:  # pragma: no cover - environment-dependent
    pyautogui = None

from config import SKIP_DUPLICATE_PHONES

# ==========================================================
# Chat focus verification tuning
# ==========================================================
SCREEN_DIFF_THRESHOLD = 0.05   # Fraction of changed pixels that means "the chat window rendered"
FOCUS_GRACE_SECONDS = 0.75     # Extra settle time after verification before pressing Enter


def _active_title():
    """
    Returns the lowercased title of the active (foreground) window, or None
    when pyautogui cannot read it on this platform (e.g. Linux).
    """
    if pyautogui is None:
        return None
    try:
        win = pyautogui.getActiveWindow()
        return (win.title or "").lower() if win is not None else ""
    except Exception:
        return None


def _screen_changed(baseline):
    """
    Compares a fresh screenshot against the pre-launch baseline and reports whether
    the screen visibly changed. Returns True/False, or None when screenshots are
    unavailable on this platform (e.g. missing scrot on Linux).
    """
    if pyautogui is None:
        return None
    try:
        shot = pyautogui.screenshot()
        if shot is None:
            return None
        a = np.asarray(baseline.convert("RGB").resize((120, 75)), dtype=np.float32)
        b = np.asarray(shot.convert("RGB").resize((120, 75)), dtype=np.float32)
        changed_ratio = float((np.abs(a - b).sum(axis=2) > 30.0).mean())
        return changed_ratio > SCREEN_DIFF_THRESHOLD
    except Exception:
        return None


def _wait_for_chat_ready(baseline, focus_timeout):
    """
    Polls until the WhatsApp Desktop chat window is confirmed focused and the new
    chat has actually rendered — the guard against pressing Enter into a stale or
    wrong window.

    Confirmation layers:
      1. Active-window title contains "whatsapp" (authoritative on Windows).
      2. Full-screen pixel diff vs. the pre-launch baseline (proves the new chat
         rendered, not just that WhatsApp happens to be focused).

    When both layers are available both must pass before Enter is pressed. When only
    one is available it alone gates the send. Returns True (verified), False (timed
    out), or None when no verification mechanism exists on this platform.

    Fail-safe edge: if the reopened chat is pixel-identical to the baseline, the diff
    never flips and the send is skipped (no blind Enter) rather than risking a stale
    window — the contact is marked FAILED and can be retried manually.
    """
    deadline = time.time() + focus_timeout

    while time.time() < deadline:
        title = _active_title()
        screen = _screen_changed(baseline) if baseline is not None else None

        # No verification possible on this platform — the caller decides how to degrade.
        if title is None and screen is None:
            return None

        title_match = title is not None and "whatsapp" in title

        if title is not None and screen is not None:
            if title_match and screen:
                return True
        elif title is not None:      # screen verification unavailable
            if title_match:
                return True
        elif screen is not None:     # title verification unavailable
            if screen:
                return True

        time.sleep(0.4)

    return False


def process_dispatch_queue(queue, wait_time, tab_close, close_time, cool_down, max_retries,
                           focus_timeout=15, log=None, confirm_ready=None):
    """
    Processes the ordered execution priority object array queue securely
    using the native Windows WhatsApp Desktop Application via URI schemes.

    Each message is only sent after the chat window has been *verified* focused
    (active-window title + screenshot diff), so Enter never lands in the wrong app.

    Note: verification confirms the WhatsApp window is focused; it cannot confirm the
    message text actually landed in the input box (e.g. when WhatsApp's URI handler
    truncates very long messages), so a send can still be logged without being delivered.

    log(line)          : optional callback receiving every progress line (in addition to stdout).
    confirm_ready()    : optional callback replacing the "press ENTER to run" gate; return
                         True to start sending or False to abort before the first dispatch.
    """
    def emit(line):
        print(line)
        if log:
            log(line)

    def audit(level, msg):
        """Routes a structured audit line to the file log AND the optional log callback
        (without printing it, so CLI console output is unchanged)."""
        getattr(logging, level)(msg)
        if log:
            log(msg)

    success, failed, skipped = 0, 0, 0
    total = len(queue)
    seen_phones = set()

    # Establish a fresh text file log trail for Feature 3
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    today_str = datetime.now().strftime('%Y.%m.%d')
    receipt_log_path = f"{log_dir}/dispatch_receipts_{today_str}.txt"

    # Make the logging.info/warning/error calls in this module actually persist (default level is WARNING)
    logging.basicConfig(
        filename=f"{log_dir}/dispatch_log_{today_str}.log",
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )

    emit(f"🚀 Actionable dispatch queue loaded: {total} items selected for delivery.")
    emit("⏳ IMPORTANT: Ensure your Windows WhatsApp Desktop Application is open and authenticated.")
    if confirm_ready is not None:
        if not confirm_ready():
            emit("🛑 Dispatch aborted by user before sending began.")
            return success, failed, skipped
    else:
        input("👉 Bring the WhatsApp window to the background, then press ENTER to run...")

    for idx, item in enumerate(queue, start=1):
        name = item["party"]
        phone = item["phone"]
        msg = item["message"]

        if not phone or phone.strip() == "+":
            emit(f"⏩ [{idx}/{total}] Skipping '{name}': Missing valid phone target configuration.")
            skipped += 1
            continue

        # Feature: Deduplicate contacts sharing the same phone number.
        if SKIP_DUPLICATE_PHONES:
            if phone in seen_phones:
                emit(f"⏩ [{idx}/{total}] Skipping '{name}': Phone {phone} already dispatched (SKIP_DUPLICATE_PHONES).")
                audit("warning", f"SKIP-DUPLICATE | {name} | {phone}")
                skipped += 1
                continue
            # Registered before the attempt: if this send fails permanently, later parties
            # sharing the same phone are still skipped (fail-safe — Enter may already have
            # been pressed, so we can't prove the first message didn't deliver).
            seen_phones.add(phone)

        # Feature 2: Time-of-Day dynamic greeting insertion
        hour = datetime.now().hour
        if hour < 12:
            greeting = "☀️ *Good Morning!*"
        elif hour < 16:
            greeting = "📊 *Good Afternoon!*"
        else:
            greeting = "🌙 *Good Evening!*"

        final_msg = f"{greeting}\n\n{msg}"

        emit(f"\n[{datetime.now().strftime('%H:%M:%S')}] [{idx}/{total}] Dispatched Target -> {name} ({phone})")

        for attempt in range(1, max_retries + 1):
            try:
                start = time.time()
                encoded_msg = quote(final_msg)
                whatsapp_uri = f"whatsapp://send/?phone={phone}&text={encoded_msg}"

                # Baseline BEFORE launching the URI so we can detect the new chat rendering.
                baseline = None
                if pyautogui is not None:
                    try:
                        baseline = pyautogui.screenshot()
                    except Exception:
                        baseline = None

                os.startfile(whatsapp_uri)

                verified = _wait_for_chat_ready(baseline, focus_timeout)
                if verified is None:
                    audit("warning", f"VERIFY-UNAVAILABLE | {name} | {phone} | No focus-verification mechanism on this platform; falling back to legacy blind send.")
                    emit(f"⚠️ [{idx}/{total}] Focus verification unavailable for '{name}' — proceeding with legacy blind send.")
                    # Verification is impossible here — keep the legacy timed wait so the
                    # window has a chance to open before Enter (original behavior).
                    time.sleep(max(5, wait_time))
                elif not verified:
                    raise RuntimeError(
                        f"WhatsApp chat window not confirmed focused within {focus_timeout}s (attempt {attempt}/{max_retries})"
                    )
                else:
                    time.sleep(FOCUS_GRACE_SECONDS)
                    emit(f"🔍 [{idx}/{total}] Chat window verified focused for '{name}'.")

                # Final focus re-check immediately before the keystroke, so a notification
                # that stole focus during the grace sleep cannot hijack the Enter key.
                title_now = _active_title()
                if title_now is not None and "whatsapp" not in title_now:
                    raise RuntimeError(
                        f"Focus lost before send: active window is now '{title_now}' (attempt {attempt}/{max_retries})"
                    )

                pyautogui.press('enter')

                elapsed = time.time() - start
                success += 1

                audit("info", f"SUCCESS | {name} | {phone} | Attempt {attempt}")

                # Feature 3: Append data instantly to our live audit ledger text file
                with open(receipt_log_path, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] SENT | {name} ({phone})\n")

                remaining = total - idx

                # Feature 2: Add dynamic anti-block variance (+1 to +3 random seconds added to cool down)
                actual_cooldown = cool_down + random.randint(1, 3)
                eta = remaining * (elapsed + actual_cooldown)
                emit(f"⏳ Dynamic ETA Remaining: {int(eta // 60)} min {int(eta % 60)} sec")

                if remaining > 0:
                    time.sleep(actual_cooldown)
                break

            except Exception as e:
                audit("warning", f"Attempt {attempt}/{max_retries} failed for {name}: {e}")
                if attempt < max_retries:
                    time.sleep(5)
                else:
                    failed += 1
                    audit("error", f"FAILED | {name} | {phone} | Exceeded limit bounds: {e}")
                    with open(receipt_log_path, "a", encoding="utf-8") as f:
                        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] FAILED | {name} ({phone}) | Error: {str(e)}\n")
                    emit(f"❌ Failed permanently after {max_retries} desktop processing loops.")

    return success, failed, skipped
