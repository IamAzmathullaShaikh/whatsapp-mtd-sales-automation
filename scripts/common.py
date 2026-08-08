"""Shared helpers for the skill library CLI (stdlib only)."""

import datetime
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "library.toml"
CURATED_DIR = ROOT / ".agents" / "skills"
EXPORT_DIR = ROOT / "export"

# Skill names must be filesystem-safe path components. The skill ecosystem
# convention is lowercase letters, digits, hyphens; source ids are owner/repo.
SKILL_NAME_RE = re.compile(r"[a-z0-9-]+")
SOURCE_RE = re.compile(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+")


def require_safe_name(name, what="skill"):
    """Raise ValueError unless name is a safe path component."""
    if not isinstance(name, str) or not SKILL_NAME_RE.fullmatch(name):
        raise ValueError(f"unsafe {what} name in bundle: {name!r}")
    return name


def require_safe_source(source):
    """Raise ValueError unless source is an owner/repo pair."""
    if not isinstance(source, str) or not SOURCE_RE.fullmatch(source):
        raise ValueError(f"unsafe source in bundle: {source!r}")
    return source


def load_library_config(path=DEFAULT_CONFIG):
    with open(path, "rb") as fh:
        return tomllib.load(fh)


def library_paths(cfg):
    """Resolve [paths] (relative to the repo root) into Path objects."""
    return {key: ROOT / value for key, value in cfg["paths"].items()}


def enabled_sources(cfg, all_=False):
    """Source dicts; all_=True ignores the enabled flag (use what's on disk)."""
    repos = cfg["sources"]["repos"]
    return [s for s in repos if all_ or s.get("enabled", False)]


def source_id(src):
    return f"{src['owner']}__{src['repo']}"


def source_root(paths, src):
    """skills/sources/<owner>/<repo> for a source dict."""
    return paths["sources"] / src["owner"] / src["repo"]


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
