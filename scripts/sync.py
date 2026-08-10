"""Clone/update upstream skill sources into skills/sources/.

The committed `skills/sources/` trees are snapshots without `.git`; when one is
found, it is wiped and re-cloned fresh (git needs a repository to fetch into).
Clones that do carry `.git` (e.g. after a previous sync) are fast-forwarded.
"""

import shutil
import subprocess

from .common import enabled_sources, source_id, source_root


def current_commit(repo_dir):
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_dir), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def sync_source(src, paths):
    """Shallow-clone (or fast-forward) one source; return its commit SHA.

    A source directory without `.git` is a committed snapshot: it is removed
    and re-cloned fresh. With `.git` present, the clone is fast-forwarded.
    """
    dest = source_root(paths, src)
    dest.mkdir(parents=True, exist_ok=True)
    if not (dest / ".git").exists():
        # committed snapshot without .git — wipe and re-clone fresh
        shutil.rmtree(dest, ignore_errors=True)
        dest.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--depth", "1", "-q", src["url"], str(dest)], check=True
        )
    else:
        subprocess.run(
            ["git", "-C", str(dest), "fetch", "-q", "--depth", "1", "origin"],
            check=False,
        )
        subprocess.run(
            ["git", "-C", str(dest), "reset", "-q", "--hard", "FETCH_HEAD"],
            check=False,
        )
    return current_commit(dest)


def sync_sources(cfg, paths, all_=False):
    """Sync every (enabled) source; return {source_id: commit_sha}."""
    result = {}
    for src in enabled_sources(cfg, all_=all_):
        sid = source_id(src)
        print(f"  sync  {sid} -> {src['url']}")
        result[sid] = sync_source(src, paths)
    return result
