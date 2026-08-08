"""Tests for the multi-company registry (companies.py)."""

import json

import pytest

import companies


def _seed_legacy(tmp_path):
    legacy = tmp_path / "user_settings.json"
    legacy.write_text(json.dumps({
        "profile": {"name": "Ravi", "designation": "SM", "agency": "Ravi Agencies"},
        "brands": {"OCW": {"name": "OC Whisky", "target_col": "OCW_TARGET",
                           "actual_col": "OCW.1", "enabled": True}},
    }))
    return legacy


class TestSlugify:
    def test_basic(self):
        assert companies.slugify("Sri Krishna Agencies") == "sri-krishna-agencies"

    def test_empty_gets_fallback(self):
        assert companies.slugify("   ") == "company"


class TestCRUD:
    def test_new_list_load_save_delete(self, tmp_path):
        base = tmp_path / "companies"
        assert companies.list_companies(base) == []
        c = companies.new_company("Ganga Distilleries", base)
        assert c["slug"] == "ganga-distilleries"
        assert companies.list_companies(base) == ["ganga-distilleries"]
        loaded = companies.load_company("ganga-distilleries", base)
        assert loaded["name"] == "Ganga Distilleries"
        assert loaded["profile"]["agency"] == "Ganga Distilleries"
        assert loaded["brands"] == {}

        loaded["brands"]["XYZ"] = {"name": "XYZ Whisky", "target_col": "XYZ_TARGET",
                                   "actual_col": "XYZ.1", "enabled": True}
        companies.save_company(loaded, base)
        assert "XYZ" in companies.load_company("ganga-distilleries", base)["brands"]

        assert companies.delete_company("ganga-distilleries", base) is True
        assert companies.list_companies(base) == []
        assert companies.delete_company("ganga-distilleries", base) is False

    def test_missing_company_returns_none(self, tmp_path):
        assert companies.load_company("nope", tmp_path / "companies") is None


class TestActive:
    def test_active_roundtrip(self, tmp_path):
        base = tmp_path / "companies"
        companies.new_company("One", base)
        companies.new_company("Two", base)
        assert companies.active_company(base) is None
        companies.set_active_company("two", base)
        assert companies.active_company(base) == "two"
        companies.set_active_company(None, base)
        assert companies.active_company(base) is None

    def test_active_must_exist(self, tmp_path):
        base = tmp_path / "companies"
        companies.new_company("One", base)
        companies.set_active_company("ghost", base)
        assert companies.active_company(base) is None  # ghost doesn't exist -> None


class TestDefaultMigration:
    def test_migrates_legacy_user_settings(self, tmp_path, monkeypatch):
        base = tmp_path / "companies"
        legacy = _seed_legacy(tmp_path)
        monkeypatch.setattr(companies, "LEGACY_SETTINGS_FILE", str(legacy))
        slug = companies.ensure_default_company(base)
        assert slug == "ravi-agencies"
        settings = companies.load_company(slug, base)
        assert settings["profile"]["name"] == "Ravi"
        assert settings["brands"]["OCW"]["name"] == "OC Whisky"

    def test_blank_default_when_no_legacy(self, tmp_path):
        base = tmp_path / "companies"
        slug = companies.ensure_default_company(base)
        assert companies.list_companies(base) == [slug]
        assert companies.active_company(base) == slug

    def test_idempotent(self, tmp_path, monkeypatch):
        base = tmp_path / "companies"
        legacy = _seed_legacy(tmp_path)
        monkeypatch.setattr(companies, "LEGACY_SETTINGS_FILE", str(legacy))
        first = companies.ensure_default_company(base)
        second = companies.ensure_default_company(base)
        assert first == second
        assert companies.list_companies(base) == [first]  # no duplicates


class TestActiveSettings:
    def test_load_and_save_active(self, tmp_path):
        base = tmp_path / "companies"
        companies.ensure_default_company(base)
        settings = companies.load_active_settings(base)
        settings["profile"]["name"] = "New Name"
        companies.save_active_settings(settings, base)
        reloaded = companies.load_active_settings(base)
        assert reloaded["profile"]["name"] == "New Name"

    def test_save_active_falls_back_to_legacy_without_companies(self, tmp_path, monkeypatch):
        # No companies dir: save_active_settings writes user_settings.json.
        monkeypatch.setattr(companies, "COMPANIES_DIR", str(tmp_path / "empty-companies"))
        monkeypatch.chdir(tmp_path)
        companies.save_active_settings({"profile": {}, "brands": {}})
        assert (tmp_path / "user_settings.json").exists()
