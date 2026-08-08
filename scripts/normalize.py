"""Normalize upstream SKILL.md files into machine-readable JSON + body.

Each skill becomes:

    skills/normalized/<owner>__<repo>/<name>/
        skill.json   # parsed frontmatter + provenance (see entry schema)
        body.md      # the markdown body with frontmatter stripped

Requires PyYAML (in requirements-dev.txt) for frontmatter parsing.
"""

import hashlib
import json
import re
import shutil

from router.tokenizer import significant_tokens

from .common import SKILL_NAME_RE, enabled_sources, source_id, source_root
from .sync import current_commit


def parse_frontmatter(text):
    """Split a SKILL.md file into (metadata_dict, body). Tolerant of odd files.

    PyYAML is imported lazily so that `skilllib import` (which never parses
    frontmatter) runs on a bare Python with no third-party packages.
    """
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    try:
        import yaml  # only needed for normalization, not import/route
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "PyYAML is required to normalize skills — run "
            "`.venv/bin/pip install -r requirements-dev.txt`") from exc
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        meta = {}
    return (meta if isinstance(meta, dict) else {}), parts[2].lstrip("\n")


def iter_skill_dirs(source_root_dir):
    """Yield every directory (excluding the repo root) that holds a SKILL.md."""
    for md in sorted(source_root_dir.rglob("SKILL.md")):
        yield md.parent


def _disambiguate(name, skill_dir, root):
    """Stable unique name for duplicate skill names within one source."""
    suffix = str(skill_dir.relative_to(root)).replace("/", "-")
    return _sanitize_name(f"{name}__{suffix}")


def _sanitize_name(name):
    """Force a name into the filesystem-safe [a-z0-9-] convention.

    Duplicate disambiguation suffixes can carry dots (e.g. `.curated`); the
    import guard requires every name to match SKILL_NAME_RE, so anything else
    must be normalized here.
    """
    cleaned = re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-")
    return cleaned or "skill"


def normalize_source(src, paths):
    """Normalize one source repo; returns the list of normalized entries."""
    root = source_root(paths, src)
    out_dir = paths["normalized"] / source_id(src)
    commit = current_commit(root)
    entries = []
    seen = {}
    for skill_dir in iter_skill_dirs(root):
        md = skill_dir / "SKILL.md"
        text = md.read_text(encoding="utf-8", errors="replace")
        meta, body = parse_frontmatter(text)
        name = meta.get("name") or skill_dir.name
        if not isinstance(name, str) or not SKILL_NAME_RE.fullmatch(name):
            name = skill_dir.name  # fall back to the directory name
        rel = str(md.relative_to(root))
        raw_name = name
        name = _sanitize_name(name)
        if name in seen:  # duplicate raw or sanitized name inside one source
            print(f"  ! dup skill name '{raw_name}' in {source_id(src)} "
                  f"({seen[name]} vs {rel}) — disambiguating")
            name = _disambiguate(name, skill_dir, root)
        seen[name] = rel
        entry = {
            "name": name,
            "source": f"{src['owner']}/{src['repo']}",
            "commit": commit,
            "source_relative_path": str(md.relative_to(root)),
            "description": str(meta.get("description", "") or ""),
            "license": str(meta.get("license", "") or ""),
            "metadata": meta.get("metadata") or {},
            "keywords": significant_tokens(str(meta.get("description", "")))[:8],
            "word_count": len(body.split()),
            "hash": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        }
        skill_dir_out = out_dir / name
        skill_dir_out.mkdir(parents=True, exist_ok=True)
        (skill_dir_out / "skill.json").write_text(
            json.dumps(entry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        (skill_dir_out / "body.md").write_text(body, encoding="utf-8")
        entries.append(entry)
    return entries


def normalize_all(cfg, paths):
    """Normalize every configured source found on disk. Returns (by_source, total).

    The normalized tree is fully derived, so it is wiped first when source
    clones exist — this keeps stale entries from removed or renamed sources
    out of the index. With no clones on disk (e.g. a freshly restored machine),
    the restored tree is left untouched for the index step.
    """
    sources = enabled_sources(cfg, all_=True)
    if any(source_root(paths, src).exists() for src in sources):
        shutil.rmtree(paths["normalized"], ignore_errors=True)
    by_source, total = {}, 0
    for src in sources:
        entries = normalize_source(src, paths)
        total += len(entries)
        if entries:
            by_source[source_id(src)] = len(entries)
            print(f"  norm  {source_id(src)}: {len(entries)} skills")
    return by_source, total
