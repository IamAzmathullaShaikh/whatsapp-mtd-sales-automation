"""Write per-source and aggregate provenance manifests (JSON)."""

import json
from collections import defaultdict

from .common import enabled_sources, now_iso


def write_manifests(cfg, paths, index):
    """Write skills/manifests/<source>.json per source + library.json aggregate.

    `index` is the dict produced by scripts.indexer.build_index.
    Returns the aggregate library manifest.
    """
    by_source = defaultdict(list)
    for s in index.get("skills", []):
        if s["source"].startswith("curated/"):
            continue  # curated project skills live in .agents/skills, not upstream manifests
        by_source[s["source"]].append(s)

    sources_cfg = {f"{s['owner']}/{s['repo']}": s for s in enabled_sources(cfg, all_=True)}
    manifest_dir = paths["manifests"]
    manifest_dir.mkdir(parents=True, exist_ok=True)

    per_source = []
    for source_key in sorted(by_source):
        skills = by_source[source_key]
        cfg_src = sources_cfg.get(source_key, {})
        doc = {
            "repo": source_key,
            "url": cfg_src.get("url", ""),
            "commit": skills[0].get("commit", ""),
            "generated_at": now_iso(),
            "skill_count": len(skills),
            "skills": sorted(s["name"] for s in skills),
        }
        file_stem = source_key.replace("/", "__")
        (manifest_dir / f"{file_stem}.json").write_text(
            json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        per_source.append(doc)

    library = {
        "generated_at": now_iso(),
        "source_count": len(per_source),
        "total_skills": index.get("skill_count", 0),
        "sources": per_source,
    }
    (manifest_dir / "library.json").write_text(
        json.dumps(library, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return library
