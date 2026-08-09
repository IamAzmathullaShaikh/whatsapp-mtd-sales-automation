"""M7 — skills bridge: registry + resolver over the built library index."""

from azmath.skills import SkillRegistry, SkillResolver
from azmath.core.config import ROOT
from scripts.common import CURATED_DIR, library_paths, load_library_config

INDEX = ROOT / "skills" / "index" / "index.json"


def test_registry_counts():
    reg = SkillRegistry(INDEX)
    assert reg.count() == 133
    sources = dict(reg.by_source())
    assert sources["curated/local"] == 11
    assert reg.get("running-tests") is not None


def test_registry_search_ranks_relevant_first():
    reg = SkillRegistry(INDEX)
    hits = reg.search("how do I run the test suite", top_k=3)
    assert "running-tests" in [h["name"] for h in hits]


def test_resolver_loads_curated_bodies():
    cfg = load_library_config()
    paths = library_paths(cfg)
    resolver = SkillResolver(INDEX, paths, top_k=3, curated_dir=CURATED_DIR)
    skills = resolver.resolve("run the test suite in this repo")
    names = [s["name"] for s in skills]
    assert "running-tests" in names
    for s in skills:
        assert s["body_excerpt"]


def test_resolver_empty_without_index(tmp_path):
    resolver = SkillResolver(tmp_path / "missing.json", {}, top_k=3)
    assert resolver.resolve("anything") == []
