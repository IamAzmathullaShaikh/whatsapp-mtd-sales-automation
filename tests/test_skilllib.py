"""Tests for the skill library: tokenizer, scoring, normalization, index, router."""

import json

import pytest

from router.scoring import rank, score_query
from router.tokenizer import ngrams, significant_tokens, tokenize
from router.router import render_route, route


# ---------------------------------------------------------------------------
# tokenizer
# ---------------------------------------------------------------------------

def test_tokenize_lowercases_and_strips_punctuation():
    assert tokenize("How do I debug flaky tests?!") == [
        "how", "do", "i", "debug", "flaky", "tests",
    ]
    assert tokenize(None) == []


def test_significant_tokens_drop_stopwords():
    tokens = significant_tokens("use when the tests are flaky and hang")
    assert "the" not in tokens and "and" not in tokens
    assert "flaky" in tokens and "tests" in tokens


def test_ngrams():
    assert ngrams(["a", "b", "c"], 2) == {"a b", "b c"}
    assert ngrams(["a"], 2) == set()


# ---------------------------------------------------------------------------
# scoring / ranking
# ---------------------------------------------------------------------------

def _doc(name, description="", keywords=()):
    return {"id": f"s/{name}", "name": name, "description": description,
            "keywords": list(keywords)}


def test_name_match_outranks_description_only():
    query = "xlsx spreadsheets"
    docs = [
        _doc("xlsx", "editing spreadsheet files"),
        _doc("docx", "spreadsheet word documents"),
    ]
    assert rank(query, docs, top_k=1)[0]["name"] == "xlsx"


def test_keywords_boost():
    query = "fix my flaky tests"
    docs = [
        _doc("code-review", keywords=["review"]),
        _doc("running-tests", keywords=["tests", "flaky", "pytest"]),
    ]
    hits = rank(query, docs, top_k=2)
    assert hits[0]["name"] == "running-tests"


def test_rank_excludes_zero_scores_and_respects_top_k():
    docs = [_doc("alpha"), _doc("beta", "unrelated content here"),
            _doc("gamma", "unrelated content here")]
    assert rank("zzz no match", docs, top_k=5) == []
    hits = rank("unrelated", docs, top_k=1)
    assert len(hits) == 1


def test_score_query_returns_zero_for_empty_query():
    assert score_query("", _doc("anything")) == 0.0


def test_bigram_bonus_for_dashed_names():
    query = "excel schema mapping"
    docs = [
        _doc("excel-schema-and-mapping"),
        _doc("excel"),
    ]
    assert rank(query, docs, top_k=1)[0]["name"] == "excel-schema-and-mapping"


# ---------------------------------------------------------------------------
# frontmatter parsing (scripts.normalize)
# ---------------------------------------------------------------------------

def test_parse_frontmatter_simple():
    from scripts.normalize import parse_frontmatter
    text = "---\nname: foo-bar\ndescription: Use when x\n---\n# Body\nhi"
    meta, body = parse_frontmatter(text)
    assert meta == {"name": "foo-bar", "description": "Use when x"}
    assert body == "# Body\nhi"


def test_parse_frontmatter_folded_and_lists():
    from scripts.normalize import parse_frontmatter
    text = (
        "---\n"
        "name: cloud-thing\n"
        "description: >-\n"
        "  Use when deploying\n"
        "  or scaling things.\n"
        "sources:\n"
        "  - one\n"
        "  - two\n"
        "---\n"
        "body here"
    )
    meta, body = parse_frontmatter(text)
    assert meta["name"] == "cloud-thing"
    assert "deploying" in meta["description"] and "scaling" in meta["description"]
    assert meta["sources"] == ["one", "two"]
    assert body == "body here"


def test_parse_frontmatter_tolerates_missing_frontmatter():
    from scripts.normalize import parse_frontmatter
    assert parse_frontmatter("just a body") == ({}, "just a body")
    assert parse_frontmatter("---\nbroken")[1].startswith("---")


# ---------------------------------------------------------------------------
# index building (scripts.indexer)
# ---------------------------------------------------------------------------

def test_derive_keywords():
    from scripts.indexer import derive_keywords
    entry = {
        "name": "running-tests",
        "metadata": {"category": "DevOps"},
        "description": "Use when tests are flaky and hang or fail inconsistently",
    }
    kws = derive_keywords(entry)
    assert kws[0] == "running" and kws[1] == "tests"
    assert "devops" in kws
    assert "flaky" in kws


def test_derive_keywords_filters_stopword_name_parts():
    from scripts.indexer import derive_keywords
    kws = derive_keywords({"name": "excel-schema-and-mapping",
                           "metadata": {}, "description": ""})
    assert "and" not in kws
    assert "excel" in kws and "schema" in kws and "mapping" in kws


def test_normalize_source_disambiguates_duplicate_names(tmp_path):
    from scripts.normalize import normalize_source
    src = {"owner": "acme", "repo": "skills", "url": ""}
    root = tmp_path / "sources" / "acme" / "skills"
    (root / "skills" / "dup").mkdir(parents=True)
    (root / "skills" / "other" / "dup").mkdir(parents=True)
    md = "---\nname: dup\ndescription: Use when x\n---\nbody"
    (root / "skills" / "dup" / "SKILL.md").write_text(md)
    (root / "skills" / "other" / "dup" / "SKILL.md").write_text(md)
    paths = {"sources": tmp_path / "sources", "normalized": tmp_path / "normalized"}
    entries = normalize_source(src, paths)
    names = sorted(e["name"] for e in entries)
    assert len(entries) == 2
    assert len(set(names)) == 2  # no silent overwrite
    out = tmp_path / "normalized" / "acme__skills"
    assert len(list(out.iterdir())) == 2  # both written to disk


def test_normalize_disambiguates_sanitize_collisions(tmp_path):
    """Different raw names that sanitize identically must not overwrite."""
    from scripts.normalize import normalize_source
    src = {"owner": "acme", "repo": "skills", "url": ""}
    root = tmp_path / "sources" / "acme" / "skills"
    (root / "a").mkdir(parents=True)
    (root / "b").mkdir(parents=True)
    (root / "a" / "SKILL.md").write_text(
        "---\nname: Foo Bar\ndescription: Use when x\n---\nbody")
    (root / "b" / "SKILL.md").write_text(
        "---\nname: foo.bar\ndescription: Use when y\n---\nbody")
    paths = {"sources": tmp_path / "sources", "normalized": tmp_path / "normalized"}
    entries = normalize_source(src, paths)
    names = sorted(e["name"] for e in entries)
    assert len(entries) == 2 and len(set(names)) == 2  # both sanitize to foo-bar
    out = tmp_path / "normalized" / "acme__skills"
    assert len(list(out.iterdir())) == 2  # no silent overwrite


def test_normalize_sanitizes_dotted_disambiguation_names(tmp_path):
    """Dotted dirs (e.g. .curated/.system) must yield import-safe names."""
    import re as _re
    from scripts.common import SKILL_NAME_RE
    from scripts.normalize import normalize_source
    src = {"owner": "openai", "repo": "skills", "url": ""}
    root = tmp_path / "sources" / "openai" / "skills"
    (root / "skills" / ".curated" / "openai-docs").mkdir(parents=True)
    (root / "skills" / ".system" / "openai-docs").mkdir(parents=True)
    md = "---\nname: openai-docs\ndescription: Use when x\n---\nbody"
    (root / "skills" / ".curated" / "openai-docs" / "SKILL.md").write_text(md)
    (root / "skills" / ".system" / "openai-docs" / "SKILL.md").write_text(md)
    paths = {"sources": tmp_path / "sources", "normalized": tmp_path / "normalized"}
    entries = normalize_source(src, paths)
    names = sorted(e["name"] for e in entries)
    assert len(names) == 2 and len(set(names)) == 2
    for n in names:
        assert SKILL_NAME_RE.fullmatch(n), n  # import-safe: no dots
    assert any("system" in n for n in names)  # disambiguated, not overwritten


def test_config_module_is_not_shadowed_by_config_dir():
    """The library's config/ dir must never shadow the app's config.py."""
    import config
    assert str(config.__file__).endswith("config.py")
    assert config.SALES_SHEET == "DATA"


# ---------------------------------------------------------------------------
# export / import bundle (scripts.bundle)
# ---------------------------------------------------------------------------

def _make_fake_library(tmp_path):
    """A minimal library on disk: curated skill + one normalized skill + index."""
    curated = tmp_path / "curated"
    (curated / "my-skill" / "SKILL.md").parent.mkdir(parents=True)
    (curated / "my-skill" / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: Use when doing the thing\nversion: 1.0.0\n---\n# My skill\nbody here")
    (curated / "README.md").write_text("# Curated manifest")

    norm = tmp_path / "normalized"
    (norm / "acme__skills" / "upstream-one").mkdir(parents=True)
    (norm / "acme__skills" / "upstream-one" / "skill.json").write_text(json.dumps({
        "name": "upstream-one", "source": "acme/skills", "commit": "abc123",
        "description": "Use when upstreaming", "metadata": {}, "word_count": 3,
    }))
    (norm / "acme__skills" / "upstream-one" / "body.md").write_text("the body")

    index = tmp_path / "index.json"
    index.write_text(json.dumps({"version": 1, "generated_at": "t", "skill_count": 1,
                                 "skills": [{"id": "acme/skills/upstream-one",
                                              "name": "upstream-one",
                                              "source": "acme/skills",
                                              "description": "Use when upstreaming",
                                              "keywords": ["upstream"]}]}))
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    (manifests / "library.json").write_text(json.dumps({
        "generated_at": "t", "source_count": 1, "total_skills": 1,
        "sources": [{"repo": "acme/skills", "url": "https://example.com",
                      "commit": "abc123", "skill_count": 1}],
    }))
    paths = {"index": index, "normalized": norm, "manifests": manifests}
    return curated, paths


def test_export_bundle_structure(tmp_path):
    from scripts.bundle import export_bundle
    curated, paths = _make_fake_library(tmp_path)
    out = tmp_path / "out"
    bundle_data, bundle_path, prompt_path = export_bundle({}, paths, curated, out)
    assert bundle_path.exists() and prompt_path.exists()
    assert bundle_data["curated_count"] == 1
    assert bundle_data["library_count"] == 1
    assert bundle_data["curated"][0]["name"] == "my-skill"
    assert bundle_data["library"]["normalized"][0]["body"] == "the body"
    prompt = prompt_path.read_text()
    assert "my-skill" in prompt and "upstream-one" in prompt
    assert "Provenance" in prompt and "acme/skills" in prompt


def test_import_roundtrip_restores_everything(tmp_path):
    from scripts.bundle import export_bundle, import_bundle
    curated, paths = _make_fake_library(tmp_path)
    out = tmp_path / "out"
    _, bundle_path, _ = export_bundle({}, paths, curated, out)

    # wipe the live dirs, then restore from the bundle alone
    import shutil
    shutil.rmtree(curated)
    shutil.rmtree(paths["normalized"])
    paths["index"].unlink()
    shutil.rmtree(paths["manifests"])

    result = import_bundle(bundle_path, curated, paths)
    assert result == {"curated": 1, "normalized": 1}

    restored = (curated / "my-skill" / "SKILL.md").read_text()
    assert "name: my-skill" in restored and "body here" in restored
    assert (curated / "README.md").read_text() == "# Curated manifest"
    body = (paths["normalized"] / "acme__skills" / "upstream-one" / "body.md").read_text()
    assert body == "the body"
    assert json.loads(paths["index"].read_text())["skill_count"] == 1
    assert (paths["manifests"] / "library.json").exists()
    assert (paths["manifests"] / "acme__skills.json").exists()


def test_import_rejects_non_bundle(tmp_path):
    from scripts.bundle import import_bundle
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"format": "something-else"}))
    with pytest.raises(ValueError):
        import_bundle(bad, tmp_path / "curated",
                      {"normalized": tmp_path, "index": tmp_path / "i.json",
                       "manifests": tmp_path})


def test_import_rejects_traversal_names(tmp_path):
    """Crafted bundle names must not escape the target directories."""
    from scripts.bundle import import_bundle
    paths = {"normalized": tmp_path / "normalized",
             "index": tmp_path / "index.json",
             "manifests": tmp_path / "manifests"}
    for name in ("../../evil", "a/b", ".."):
        bad = tmp_path / f"bad-{abs(hash(name))}.json"
        bad.write_text(json.dumps({
            "format": "whatsapp-skill-library-bundle", "version": 1,
            "curated": [{"name": name, "full_markdown": "# x"}],
            "library": {"normalized": [], "index": None, "manifests": {}},
        }))
        with pytest.raises(ValueError):
            import_bundle(bad, tmp_path / "curated", paths)
        assert not (tmp_path / "..").resolve().joinpath("evil").exists()
    # a malicious source field is rejected too
    bad_src = tmp_path / "bad-src.json"
    bad_src.write_text(json.dumps({
        "format": "whatsapp-skill-library-bundle", "version": 1,
        "curated": [],
        "library": {"normalized": [{"name": "ok", "source": "../../evil", "body": ""}],
                     "index": None, "manifests": {}},
    }))
    with pytest.raises(ValueError):
        import_bundle(bad_src, tmp_path / "curated", paths)


def test_import_roundtrip_unicode_bodies(tmp_path):
    import shutil
    from scripts.bundle import import_bundle, export_bundle
    curated = tmp_path / "curated"
    (curated / "uni-skill" / "SKILL.md").parent.mkdir(parents=True)
    (curated / "uni-skill" / "SKILL.md").write_text(
        "---\nname: uni-skill\ndescription: Use when unicode\n---\n# Ünïcode héadér 中文")
    (curated / "README.md").write_text("# manifest")
    norm = tmp_path / "normalized"
    (norm / "acme__skills" / "one").mkdir(parents=True)
    (norm / "acme__skills" / "one" / "skill.json").write_text(json.dumps({
        "name": "one", "source": "acme/skills", "commit": "c",
        "description": "Üse whën ünicode", "metadata": {}, "word_count": 1,
    }))
    (norm / "acme__skills" / "one" / "body.md").write_text("bödy 中文")
    paths = {"index": tmp_path / "index.json", "normalized": norm,
             "manifests": tmp_path / "manifests"}
    (paths["manifests"]).mkdir()
    (paths["manifests"] / "library.json").write_text(json.dumps({
        "generated_at": "t", "source_count": 1, "total_skills": 1,
        "sources": [{"repo": "acme/skills", "url": "u", "commit": "c",
                      "skill_count": 1}],
    }))
    paths["index"].write_text(json.dumps({"version": 1, "generated_at": "t",
                                           "skill_count": 1, "skills": []}))
    out = tmp_path / "out"
    _, bundle_path, _ = export_bundle({}, paths, curated, out)

    shutil.rmtree(curated)
    shutil.rmtree(paths["normalized"])
    paths["index"].unlink()
    shutil.rmtree(paths["manifests"])
    import_bundle(bundle_path, curated, paths)

    assert "中文" in (curated / "uni-skill" / "SKILL.md").read_text()
    assert "bödy 中文" in (paths["normalized"] / "acme__skills" / "one" / "body.md").read_text()
    assert "Üse whën" in (paths["normalized"] / "acme__skills" / "one" / "skill.json").read_text()


def test_build_index_from_normalized_tree(tmp_path):
    from scripts.indexer import build_index
    cfg = {"paths": {}, "sources": {}}
    norm = tmp_path / "normalized"
    (norm / "acme__skills" / "one").mkdir(parents=True)
    (norm / "acme__skills" / "one" / "skill.json").write_text(json.dumps({
        "name": "one", "source": "acme/skills", "commit": "abc123",
        "description": "Use when doing the thing", "metadata": {},
    }))
    paths = {"normalized": norm, "index": tmp_path / "index.json"}
    index = build_index(cfg, paths)
    assert index["skill_count"] == 1
    assert index["skills"][0]["id"] == "acme/skills/one"
    assert "thing" in index["skills"][0]["keywords"]


# ---------------------------------------------------------------------------
# manifests (scripts.manifests)
# ---------------------------------------------------------------------------

def test_write_manifests(tmp_path):
    from scripts.manifests import write_manifests
    cfg = {"sources": {"repos": [
        {"owner": "acme", "repo": "skills", "url": "https://example.com/acme/skills"},
    ]}}
    index = {"skill_count": 2, "skills": [
        {"name": "a", "source": "acme/skills", "commit": "sha1"},
        {"name": "b", "source": "acme/skills", "commit": "sha1"},
    ]}
    paths = {"manifests": tmp_path / "manifests"}
    library = write_manifests(cfg, paths, index)
    assert library["total_skills"] == 2
    assert library["source_count"] == 1
    per = json.loads((paths["manifests"] / "acme__skills.json").read_text())
    assert per["skills"] == ["a", "b"]
    assert per["url"] == "https://example.com/acme/skills"


# ---------------------------------------------------------------------------
# router end-to-end
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_index(tmp_path):
    index = {
        "version": 1,
        "generated_at": "2026-01-01T00:00:00Z",
        "skill_count": 3,
        "skills": [
            {"id": "a/xlsx", "name": "xlsx", "source": "a/skills",
             "description": "Use when a spreadsheet file is the input or output",
             "keywords": ["xlsx", "spreadsheet", "excel"], "commit": "c1"},
            {"id": "a/docx", "name": "docx", "source": "a/skills",
             "description": "Use when a Word document is the deliverable",
             "keywords": ["docx", "word", "document"], "commit": "c1"},
            {"id": "b/code-review", "name": "code-review", "source": "b/skills",
             "description": "Use when reviewing a diff or pull request",
             "keywords": ["review", "diff", "pr"], "commit": "c2"},
        ],
    }
    p = tmp_path / "index.json"
    p.write_text(json.dumps(index))
    return p


def test_route_returns_best_hit(sample_index):
    hits, index = route("review this pull request diff", sample_index, top_k=2)
    assert hits[0]["name"] == "code-review"
    assert index["skill_count"] == 3


def test_route_excel_query(sample_index):
    hits, _ = route("open my xlsx and add a formula", sample_index, top_k=1)
    assert hits[0]["name"] == "xlsx"


def test_route_no_match(sample_index):
    hits, _ = route("quantum chromodynamics", sample_index, top_k=5)
    assert hits == []


def test_render_route_fills_template():
    template = "Query: {{query}}\nTop {{top_k}}:\n{{ranked}}"
    out = render_route("my query", [{"name": "xlsx", "source": "a/skills",
                                     "description": "short desc"}], 1, template)
    assert "Query: my query" in out
    assert "Top 1:" in out
    assert "xlsx" in out and "short desc" in out
