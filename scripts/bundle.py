"""Export/import the skill library as a portable, self-contained bundle.

Two artifacts are produced by `skilllib export`:

- `export/skills-bundle.json` — the complete data file: every curated skill
  (full SKILL.md text), every normalized library skill (metadata + full body),
  the index, and the manifests. Self-contained; importable offline.
- `export/skills-prompt.md` — a prompt pack: the same content rendered as a
  structured markdown document another model can be handed directly.

`skilllib import <bundle.json>` restores the curated set, the normalized tree,
the index, and the manifests — no network required.
"""

import json
from pathlib import Path

from .common import now_iso, require_safe_name, require_safe_source

BUNDLE_FORMAT = "whatsapp-skill-library-bundle"
BUNDLE_VERSION = 1


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

def collect_curated(curated_dir):
    """Every curated skill as {name, path, full_markdown}."""
    curated = []
    for sk in sorted(Path(curated_dir).glob("*/SKILL.md")):
        curated.append({
            "name": sk.parent.name,
            "path": str(sk.relative_to(curated_dir)),
            "full_markdown": sk.read_text(encoding="utf-8", errors="replace"),
        })
    return curated


def _collect_normalized(paths):
    """Every normalized skill with its body inlined."""
    normalized = []
    for jf in sorted(paths["normalized"].rglob("skill.json")):
        entry = json.loads(jf.read_text(encoding="utf-8"))
        body_path = jf.parent / "body.md"
        normalized.append({
            **entry,
            "body": body_path.read_text(encoding="utf-8", errors="replace"),
        })
    return normalized


def build_bundle(cfg, paths, curated_dir):
    """Assemble the full bundle dict from the live library on disk."""
    index = json.loads(paths["index"].read_text(encoding="utf-8"))
    lib_manifest = json.loads(
        (paths["manifests"] / "library.json").read_text(encoding="utf-8"))
    curated = collect_curated(curated_dir)
    readme = Path(curated_dir) / "README.md"
    return {
        "format": BUNDLE_FORMAT,
        "version": BUNDLE_VERSION,
        "exported_at": now_iso(),
        "curated_count": len(curated),
        "library_count": index.get("skill_count", 0),
        "curated_readme": readme.read_text(encoding="utf-8", errors="replace")
        if readme.exists() else None,
        "curated": curated,
        "library": {
            "index": index,
            "normalized": _collect_normalized(paths),
            "manifests": lib_manifest,
        },
    }


def export_bundle(cfg, paths, curated_dir, out_dir):
    """Write skills-bundle.json + skills-prompt.md into out_dir."""
    bundle = build_bundle(cfg, paths, curated_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = out_dir / "skills-bundle.json"
    bundle_path.write_text(
        json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    prompt_path = out_dir / "skills-prompt.md"
    prompt_path.write_text(render_prompt_pack(bundle), encoding="utf-8")
    return bundle, bundle_path, prompt_path


# ---------------------------------------------------------------------------
# prompt pack
# ---------------------------------------------------------------------------

def render_prompt_pack(bundle):
    """Render the bundle as a portable markdown prompt document."""
    curated = bundle.get("curated", [])
    normalized = bundle["library"].get("normalized", [])
    manifests = bundle["library"].get("manifests", {})
    n_sources = manifests.get("source_count", 0)

    lines = [
        "# 🧠 Skill Library — Portable Prompt Pack",
        "",
        f"> Generated {bundle['exported_at']} · bundle format v{bundle['version']} · "
        f"{len(curated)} curated project skills + {len(normalized)} library skills "
        f"from {n_sources} sources.",
        "> Machine-readable twin: `skills-bundle.json` (restore offline with "
        "`python -m scripts.skilllib import export/skills-bundle.json`).",
        "",
        "## For the receiving model",
        "",
        "This pack transfers an entire skill library so you can act on it without redoing research.",
        "",
        "1. **Curated project skills** (Section 1) are complete skills written for this codebase — follow them when their trigger matches the task.",
        "2. **Library skills** (Section 2) are upstream ecosystem skills, each with its when-to-use description and full body — use them as references; this repository's own conventions win on conflict.",
        "3. **Provenance** (Section 3) pins every source to a repo + commit SHA.",
        "4. Restore on any machine: `python -m scripts.skilllib import export/skills-bundle.json` (works offline).",
        "5. Routing discipline: a skill's description states WHEN to use it — never treat it as a summary of its steps.",
        "",
        "---",
        "",
        "## Section 1 — Curated project skills",
        "",
    ]
    for c in curated:
        lines.append(f"### skill: {c['name']} (curated — {c['path']})")
        lines.append("")
        lines.append(c["full_markdown"])
        lines.append("")

    lines += ["---", "", "## Section 2 — Library skills", ""]
    for e in normalized:
        lines.append(f"### skill: {e['name']} [{e['source']}]")
        lines.append("")
        desc = str(e.get("description", "")) or "(no description)"
        lines.append(f"**When to use:** {desc}")
        lines.append("")
        lines.append(e.get("body", ""))
        lines.append("")

    lines += ["---", "", "## Section 3 — Provenance", "",
              "| Source | Commit | Skills |", "|---|---|---|"]
    for s in manifests.get("sources", []):
        lines.append(f"| {s.get('repo')} | `{s.get('commit')}` | {s.get('skill_count')} |")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# import
# ---------------------------------------------------------------------------

def import_bundle(bundle_path, curated_dir, paths):
    """Restore curated skills, normalized tree, index, and manifests offline."""
    bundle = json.loads(Path(bundle_path).read_text(encoding="utf-8"))
    if bundle.get("format") != BUNDLE_FORMAT:
        raise ValueError(f"{bundle_path} is not a skill library bundle")

    # Validate every name/source BEFORE writing anything: a crafted bundle
    # must not be able to escape the target directories via path traversal.
    for c in bundle.get("curated", []):
        require_safe_name(c.get("name"), "curated skill")
    for e in bundle.get("library", {}).get("normalized", []):
        require_safe_source(e.get("source", ""))
        require_safe_name(e.get("name"), "library skill")

    curated_dir = Path(curated_dir)
    curated_dir.mkdir(parents=True, exist_ok=True)
    for c in bundle.get("curated", []):
        target = curated_dir / c["name"] / "SKILL.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(c["full_markdown"], encoding="utf-8")
    if bundle.get("curated_readme"):
        (curated_dir / "README.md").write_text(bundle["curated_readme"], encoding="utf-8")

    library = bundle.get("library", {})
    for e in library.get("normalized", []):
        out = paths["normalized"] / e["source"].replace("/", "__") / e["name"]
        out.mkdir(parents=True, exist_ok=True)
        entry = {k: v for k, v in e.items() if k != "body"}
        (out / "skill.json").write_text(
            json.dumps(entry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (out / "body.md").write_text(e.get("body", ""), encoding="utf-8")

    if library.get("index"):
        paths["index"].parent.mkdir(parents=True, exist_ok=True)
        paths["index"].write_text(
            json.dumps(library["index"], indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")

    manifests_dir = paths["manifests"]
    manifests_dir.mkdir(parents=True, exist_ok=True)
    for s in library.get("manifests", {}).get("sources", []):
        key = s.get("repo", "").replace("/", "__")
        (manifests_dir / f"{key}.json").write_text(
            json.dumps(s, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (manifests_dir / "library.json").write_text(
        json.dumps(library.get("manifests", {}), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")

    return {"curated": len(bundle.get("curated", [])),
            "normalized": len(library.get("normalized", []))}
