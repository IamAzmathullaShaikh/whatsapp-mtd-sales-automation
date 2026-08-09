"""M2 — model provider abstraction + registry."""

import pytest

from azmath.models import ProviderError, ProviderRegistry
from azmath.models.base import ModelProvider


class FakeProvider:
    name = "fake"

    def __init__(self, healthy=True, name="fake"):
        self.name = name
        self.healthy = healthy

    def health(self):
        return self.healthy

    def generate(self, prompt, **kwargs):
        return f"echo: {prompt[:10]}"

    def metadata(self):
        return {"provider": "fake"}


def test_provider_is_a_protocol():
    assert isinstance(FakeProvider(), ModelProvider)


def test_registry_register_lookup_list():
    reg = ProviderRegistry()
    reg.register(FakeProvider(), alias="f")
    assert reg.get("fake") is reg.get("f")
    assert "fake" in reg
    assert reg.list() == ["fake"]


def test_registry_unknown_raises():
    reg = ProviderRegistry()
    with pytest.raises(KeyError):
        reg.get("nope")


def test_available_filters_unhealthy():
    reg = ProviderRegistry()
    reg.register(FakeProvider(healthy=True, name="good"))
    reg.register(FakeProvider(healthy=False, name="bad"))
    assert reg.available() == ["good"]


def test_provider_error_message():
    err = ProviderError("boom", cause=ValueError("x"))
    assert str(err) == "boom"
