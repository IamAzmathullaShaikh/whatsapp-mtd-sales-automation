"""Build the searchable skill index from the normalized tree + curated set."""

import hashlib
import json
from collections import Counter
from pathlib import Path

from router.tokenizer import STOPWORDS, significant_tokens

from .common import now_iso


def derive_keywords(entry):
    """Index keywords: name parts + category + frequent description tokens."""
    kws = [part for part in entry.get("name", "").split("-")
           if part and part not in STOPWORDS]
    category = str((entry.get("metadata") or {}).get("category", ""))
    if category:
        kws.append(category.lower())
    kws += [w for w, _ in Counter(
        significant_tokens(entry.get("description", ""))).most_common(6)]
    seen, out = set(), []
    for w in kws:
        w = w.lower()
        if w and w not in seen:
            seen.add(w)
            out.append(w)
    return out


def collect_curated(curated_dir):
    """Add the curated .agents/skills set to the index as source 'curated/local'.

    This is the guide's "project skills" tier: the agent can route to skills
    written for this codebase (run tests, launch the GUI, dispatch pipeline).
    """
    from scripts.normalize import parse_frontmatter

    items = []
    for sk in sorted(Path(curated_dir).glob("*/SKILL.md")):
        text = sk.read_text(encoding="utf-8", errors="replace")
        meta, body = parse_frontmatter(text)
        name = meta.get("name") or sk.parent.name
        if not isinstance(name, str):
            name = sk.parent.name
        description = str(meta.get("description", "") or "")
        items.append({
            "name": name,
            "source": "curated/local",
            "commit": "",
            "source_relative_path": str(sk.relative_to(Path(curated_dir))),
            "description": description,
            "license": str(meta.get("license", "") or ""),
            "metadata": meta.get("metadata") or {},
            "keywords": derive_keywords({"name": name, "metadata": meta.get("metadata") or {},
                                         "description": description}),
            "word_count": len(body.split()),
            "hash": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            "id": f"curated/local/{name}",
        })
    return items


def build_index(cfg, paths, curated_dir=None):
    """Walk skills/normalized (plus curated skills when a curated dir is given)
    and write skills/index/index.json."""
    skills = []
    for jf in sorted(paths["normalized"].rglob("skill.json")):
        entry = json.loads(jf.read_text(encoding="utf-8"))
        skills.append({
            **entry,
            "id": f"{entry['source']}/{entry['name']}",
            "keywords": derive_keywords(entry),
        })
    if curated_dir:
        skills += collect_curated(curated_dir)
    index = {
        "version": 1,
        "generated_at": now_iso(),
        "skill_count": len(skills),
        "skills": skills,
    }
    paths["index"].parent.mkdir(parents=True, exist_ok=True)
    paths["index"].write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return index
