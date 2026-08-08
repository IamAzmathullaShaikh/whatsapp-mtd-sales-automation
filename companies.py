"""
Multi-company registry: one settings file per alcohol-beverage company.

Each company lives at ``companies/<slug>.json`` and carries everything that
differs between companies:

    {
      "name": "Sri Krishna Agencies",
      "slug": "sri-krishna-agencies",
      "profile": {"name": "...", "designation": "...", "agency": "..."},
      "brands": {CODE: {"name", "target_col", "actual_col", "enabled"}},
      "party_master": "party_master.xlsx",      # per-company master file (optional)
      "sales_prefix": "Outlet_Wise_Sales_",     # file prefix used to auto-detect MTD dumps
      "schema": {                              # per-file-type MTD mappings (auto-detected)
        "sales": {"sheet": "DATA", "header_row": 4,
                   "columns": {"depot": "Name Of Depot", "syndicate": "SYNDICATE NAME",
                                "vendor": "VENDOR_NAME", "total": "Total"}},
        "party": {"sheet": None, "header_row": 0,
                   "columns": {"party": "PARTY", "phone": "PHONE", "send": "SEND",
                                "priority": "PRIORITY", "total_target": "TOTAL_TARGET"}}
      }
    }

Every function takes an optional ``base_dir`` so tests can run against a
temporary directory; production code uses the module-level COMPANIES_DIR.
"""

import json
import os
import re
from pathlib import Path

COMPANIES_DIR = "companies"
ACTIVE_FILE = "active.txt"
LEGACY_SETTINGS_FILE = "user_settings.json"

SLUG_RE = re.compile(r"[^a-z0-9-]+")


def slugify(name):
    """'Sri Krishna Agencies' -> 'sri-krishna-agencies' (import-safe slug)."""
    slug = SLUG_RE.sub("-", name.strip().lower()).strip("-")
    return slug or "company"


def _company_path(slug, base_dir):
    return Path(base_dir) / f"{slug}.json"


def list_companies(base_dir=None):
    """Sorted slugs of every company on disk (companies/<slug>.json)."""
    base_dir = base_dir or COMPANIES_DIR
    if not os.path.isdir(base_dir):
        return []
    return sorted(
        p.stem for p in Path(base_dir).glob("*.json")
        if p.name != "sample.json.example"
    )


def load_company(slug, base_dir=None):
    """Load one company's settings, or None when it does not exist."""
    base_dir = base_dir or COMPANIES_DIR
    path = _company_path(slug, base_dir)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_company(settings, base_dir=None):
    """Persist a company's settings (creating companies/ as needed)."""
    base_dir = base_dir or COMPANIES_DIR
    os.makedirs(base_dir, exist_ok=True)
    slug = settings.get("slug") or slugify(settings.get("name", "company"))
    settings["slug"] = slug
    with open(_company_path(slug, base_dir), "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
    return slug


def delete_company(slug, base_dir=None):
    """Remove a company's settings file. Returns True when it existed."""
    base_dir = base_dir or COMPANIES_DIR
    path = _company_path(slug, base_dir)
    if not path.exists():
        return False
    os.remove(path)
    if active_company(base_dir) == slug:
        set_active_company(None, base_dir)
    return True


def new_company(name, base_dir=None):
    """Create a fresh company from the name. Returns its settings dict."""
    settings = {
        "name": name,
        "slug": slugify(name),
        "profile": {"name": "", "designation": "", "agency": name},
        "brands": {},
        "party_master": "party_master.xlsx",
        "sales_prefix": "Outlet_Wise_Sales_",
        "schema": {"sales": {"sheet": None, "header_row": None, "columns": {}},
                    "party": {"sheet": None, "header_row": None, "columns": {}}},
    }
    save_company(settings, base_dir)
    return settings


def active_company(base_dir=None):
    """Slug of the currently selected company, or None."""
    base_dir = base_dir or COMPANIES_DIR
    path = Path(base_dir) / ACTIVE_FILE
    if not path.exists():
        return None
    slug = path.read_text(encoding="utf-8").strip()
    return slug if slug and load_company(slug, base_dir) else None


def set_active_company(slug, base_dir=None):
    """Persist the active company selection (None clears it)."""
    base_dir = base_dir or COMPANIES_DIR
    os.makedirs(base_dir, exist_ok=True)
    path = Path(base_dir) / ACTIVE_FILE
    if slug:
        path.write_text(slug, encoding="utf-8")
    elif path.exists():
        os.remove(path)


def ensure_default_company(base_dir=None):
    """
    First-run migration: when no companies exist yet, seed the active company
    from the legacy user_settings.json (or a blank default) so existing users
    keep their profile/brands unchanged. Returns the active slug.
    """
    base_dir = base_dir or COMPANIES_DIR
    companies = list_companies(base_dir)
    if companies:
        active = active_company(base_dir)
        if active:
            return active
        # companies exist but none active -> pick the first one deterministically
        set_active_company(companies[0], base_dir)
        return companies[0]

    legacy = None
    legacy_path = Path(LEGACY_SETTINGS_FILE)
    if legacy_path.exists():
        try:
            legacy = json.loads(legacy_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            legacy = None

    name = "Default Company"
    profile = {"name": "", "designation": "", "agency": name}
    brands = {}
    if legacy:
        name = legacy.get("profile", {}).get("agency") or legacy.get("profile", {}).get("name") or name
        profile = legacy.get("profile", profile)
        brands = legacy.get("brands", {})

    settings = {
        "name": name,
        "slug": slugify(name),
        "profile": profile,
        "brands": brands,
        "party_master": "party_master.xlsx",
        "sales_prefix": "Outlet_Wise_Sales_",
        "schema": {"sales": {"sheet": None, "header_row": None, "columns": {}},
                    "party": {"sheet": None, "header_row": None, "columns": {}}},
    }
    save_company(settings, base_dir)
    set_active_company(settings["slug"], base_dir)
    return settings["slug"]


def load_active_settings(base_dir=None):
    """The active company's settings (running first-run migration if needed)."""
    base_dir = base_dir or COMPANIES_DIR
    slug = ensure_default_company(base_dir)
    settings = load_company(slug, base_dir)
    if settings is None:  # safety: never hand back None to the UI
        settings = new_company(slug or "default", base_dir)
    return settings


def save_active_settings(settings, base_dir=None):
    """Persist settings to the active company (falling back to legacy file)."""
    base_dir = base_dir or COMPANIES_DIR
    slug = active_company(base_dir)
    if slug and load_company(slug, base_dir) is not None:
        settings["slug"] = slug
        settings["name"] = settings.get("name") or slug
        return save_company(settings, base_dir)
    # No companies yet (legacy mode) -> keep writing user_settings.json
    with open(LEGACY_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
    return None
