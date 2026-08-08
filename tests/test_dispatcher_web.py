"""
Tests for dispatcher_web.py (the Linux WhatsApp Web / Selenium backend).

The orchestrator is exercised with a fake driver + patched DOM helpers, so the
test suite never needs a real browser. Only the queue/verification/counting
logic is under test — exactly the contract that must match dispatcher.py.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dispatcher_web
from dispatcher_web import (
    COMPOSE_SEL, CHATLIST_SEL, INVALID_POPUP_SEL, SEND_URL,
    phone_digits, compose_text, message_matches,
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------
class FakeElement:
    def __init__(self, text=""):
        self.text = text
        self.clicked = False
        self.sent_keys = []

    def click(self):
        self.clicked = True

    def send_keys(self, *keys):
        self.sent_keys.append(keys)
        if keys and isinstance(keys[-1], str):
            self.text = keys[-1]


class FakeDriver:
    """Records navigation; `phone` drives DOM simulation in fake_find."""

    def __init__(self, phone="OK"):
        self.phone = phone
        self.visited = []
        self.quit_called = False
        self.logged_in = True

    def get(self, url):
        self.visited.append(url)

    def quit(self):
        self.quit_called = True


def fake_find(driver, css, timeout):
    if css == CHATLIST_SEL:
        return FakeElement("chatlist") if driver.logged_in else None
    if css == COMPOSE_SEL:
        return FakeElement("") if driver.phone != "NOCOMPOSE" else None
    if css == INVALID_POPUP_SEL:
        if driver.phone == "INVALID":
            return FakeElement("The phone number shared via url is invalid")
        return None
    return None


def make_item(party="Acme", phone="+919876543210", message="Hello *Acme*!"):
    return {"party": party, "phone": phone, "message": message}


@pytest.fixture
def patched(monkeypatch):
    sent = []

    def fake_create_driver(user_data_dir, headless=False):
        return FakeDriver()

    def fake_send_keys(el, text):
        el.text = text
        sent.append(text)

    monkeypatch.setattr(dispatcher_web, "_create_driver", fake_create_driver)
    monkeypatch.setattr(dispatcher_web, "_find", fake_find)
    monkeypatch.setattr(dispatcher_web, "_send_keys", fake_send_keys)
    monkeypatch.setattr(dispatcher_web.time, "sleep", lambda *a, **k: None)
    monkeypatch.setattr(sys, "stdin", type("S", (), {"readline": lambda self: "\n"})())
    return sent


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------
class TestHelpers:
    def test_phone_digits_strips_plus_and_punctuation(self):
        assert phone_digits("+91 98765-43210") == "919876543210"
        assert phone_digits("9876543210") == "9876543210"

    def test_phone_digits_empty(self):
        assert phone_digits("+") == ""
        assert phone_digits("") == ""

    def test_compose_text_normalizes_whitespace(self):
        el = FakeElement("  Hello   World\nnext ")
        assert compose_text(el) == "Hello World next"

    def test_message_matches_exact(self):
        assert message_matches(FakeElement("Hello Acme"), "Hello Acme") is True

    def test_message_matches_whitespace_insensitive(self):
        assert message_matches(FakeElement("Hello\nAcme"), "Hello Acme") is True

    def test_message_matches_wrong(self):
        assert message_matches(FakeElement("Goodbye"), "Hello Acme") is False


# ---------------------------------------------------------------------------
# Orchestrator: counts, dedup, abort paths
# ---------------------------------------------------------------------------
class TestOrchestrator:
    def test_full_run_success_counts(self, patched, monkeypatch):
        monkeypatch.setattr(dispatcher_web, "_create_driver", lambda ud, headless=False: FakeDriver())
        monkeypatch.setattr(dispatcher_web, "_ensure_logged_in", lambda driver, t, log=None: True)
        queue = [make_item("A", "+919111111111"), make_item("B", "+919222222222")]
        s, f, sk = dispatcher_web.process_dispatch_queue_web(
            queue, 0, False, 0, 0, 2, 15, log=None, confirm_ready=lambda: True)
        assert (s, f, sk) == (2, 0, 0)

    def test_invalid_number_failed(self, patched, monkeypatch):
        monkeypatch.setattr(dispatcher_web, "_create_driver", lambda ud, headless=False: FakeDriver("INVALID"))
        monkeypatch.setattr(dispatcher_web, "_ensure_logged_in", lambda driver, t, log=None: True)
        queue = [make_item("A", "+919111111111")]
        s, f, sk = dispatcher_web.process_dispatch_queue_web(
            queue, 0, False, 0, 0, 2, 15, log=None, confirm_ready=lambda: True)
        assert (s, f, sk) == (0, 1, 0)

    def test_verification_failure_failed(self, patched, monkeypatch):
        monkeypatch.setattr(dispatcher_web, "_create_driver", lambda ud, headless=False: FakeDriver("NOCOMPOSE"))
        monkeypatch.setattr(dispatcher_web, "_ensure_logged_in", lambda driver, t, log=None: True)
        queue = [make_item("A", "+919111111111")]
        s, f, sk = dispatcher_web.process_dispatch_queue_web(
            queue, 0, False, 0, 0, 2, 15, log=None, confirm_ready=lambda: True)
        assert (s, f, sk) == (0, 1, 0)

    def test_duplicate_phone_skipped(self, patched, monkeypatch):
        monkeypatch.setattr(dispatcher_web, "_create_driver", lambda ud, headless=False: FakeDriver())
        monkeypatch.setattr(dispatcher_web, "_ensure_logged_in", lambda driver, t, log=None: True)
        queue = [make_item("A", "+919111111111"), make_item("B", "+919111111111")]
        s, f, sk = dispatcher_web.process_dispatch_queue_web(
            queue, 0, False, 0, 0, 2, 15, log=None, confirm_ready=lambda: True)
        assert (s, f, sk) == (1, 0, 1)

    def test_missing_phone_skipped(self, patched, monkeypatch):
        monkeypatch.setattr(dispatcher_web, "_create_driver", lambda ud, headless=False: FakeDriver())
        monkeypatch.setattr(dispatcher_web, "_ensure_logged_in", lambda driver, t, log=None: True)
        queue = [make_item("A", "+")]
        s, f, sk = dispatcher_web.process_dispatch_queue_web(
            queue, 0, False, 0, 0, 2, 15, log=None, confirm_ready=lambda: True)
        assert (s, f, sk) == (0, 0, 1)

    def test_confirm_ready_abort_sends_nothing(self, patched, monkeypatch):
        monkeypatch.setattr(dispatcher_web, "_create_driver", lambda ud, headless=False: FakeDriver())
        monkeypatch.setattr(dispatcher_web, "_ensure_logged_in", lambda driver, t, log=None: True)
        queue = [make_item("A", "+919111111111")]
        s, f, sk = dispatcher_web.process_dispatch_queue_web(
            queue, 0, False, 0, 0, 2, 15, log=None, confirm_ready=lambda: False)
        assert (s, f, sk) == (0, 0, 0)

    def test_not_logged_in_aborts(self, patched, monkeypatch):
        monkeypatch.setattr(dispatcher_web, "_create_driver", lambda ud, headless=False: FakeDriver())
        monkeypatch.setattr(dispatcher_web, "_ensure_logged_in",
                            lambda driver, t: (_ for _ in ()).throw(RuntimeError("not logged in")))
        queue = [make_item("A", "+919111111111")]
        s, f, sk = dispatcher_web.process_dispatch_queue_web(
            queue, 0, False, 0, 0, 2, 15, log=None, confirm_ready=lambda: True)
        assert (s, f, sk) == (0, 0, 0)

    def test_send_url_uses_digits_only(self, patched, monkeypatch):
        driver = FakeDriver()
        monkeypatch.setattr(dispatcher_web, "_create_driver", lambda ud, headless=False: driver)
        monkeypatch.setattr(dispatcher_web, "_ensure_logged_in", lambda driver, t, log=None: True)
        queue = [make_item("A", "+91 91111 11111")]
        dispatcher_web.process_dispatch_queue_web(
            queue, 0, False, 0, 0, 2, 15, log=None, confirm_ready=lambda: True)
        assert SEND_URL.format(phone="919111111111") in driver.visited  # 91 + 10 digits
        assert driver.visited[0] == dispatcher_web.WA_WEB_URL  # home first

    def test_greeting_prepended_to_message(self, patched, monkeypatch):
        sent = patched
        monkeypatch.setattr(dispatcher_web, "_create_driver", lambda ud, headless=False: FakeDriver())
        monkeypatch.setattr(dispatcher_web, "_ensure_logged_in", lambda driver, t, log=None: True)
        queue = [make_item("A", "+919111111111", "Body message")]
        dispatcher_web.process_dispatch_queue_web(
            queue, 0, False, 0, 0, 2, 15, log=None, confirm_ready=lambda: True)
        assert sent, "expected the message to be typed into the compose box"
        assert "Body message" in sent[0]
        assert "Good" in sent[0]  # morning/afternoon/evening greeting prefix

    def test_driver_quit_after_run(self, patched, monkeypatch):
        driver = FakeDriver()
        monkeypatch.setattr(dispatcher_web, "_create_driver", lambda ud, headless=False: driver)
        monkeypatch.setattr(dispatcher_web, "_ensure_logged_in", lambda driver, t, log=None: True)
        dispatcher_web.process_dispatch_queue_web(
            [make_item()], 0, False, 0, 0, 2, 15, log=None, confirm_ready=lambda: True)
        assert driver.quit_called is True
