"""Skill library CLI.

    python -m scripts.skilllib sync                 # clone/update enabled sources
    python -m scripts.skilllib sync --all           # ... every configured source
    python -m scripts.skilllib build                # normalize + index + manifests
    python -m scripts.skilllib route "query" [-k N] # route a task to skills
    python -m scripts.skilllib stats                # index summary
    python -m scripts.skilllib chat                 # interactive REPL (re-routes every turn)
    python -m scripts.skilllib agent "task"         # one-shot: route + ask the local model
"""

import argparse
import json
import sys
from pathlib import Path

from router.router import render_route, route

from . import bundle, indexer, manifests, normalize, sync
from .common import (CURATED_DIR, DEFAULT_CONFIG, EXPORT_DIR, load_library_config,
                     library_paths)
from .common import ROOT

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


def _load():
    cfg = load_library_config()
    paths = library_paths(cfg)
    return cfg, paths


def cmd_sync(args, cfg, paths):
    synced = sync.sync_sources(cfg, paths, all_=args.all)
    print(f"\nsynced {len(synced)} source(s):")
    for sid, commit in synced.items():
        print(f"  {sid} @ {commit}")


def cmd_build(args, cfg, paths):
    by_source, total = normalize.normalize_all(cfg, paths)
    fallback = False
    if total == 0:
        existing = list(paths["normalized"].rglob("skill.json"))
        if existing:
            print(f"no source clones on disk — rebuilding index/manifests from the "
                  f"restored normalized tree ({len(existing)} skills)")
            fallback = True
        else:
            print("no sources found on disk — run `python -m scripts.skilllib sync` first")
            return
    index = indexer.build_index(cfg, paths, curated_dir=CURATED_DIR)
    library = manifests.write_manifests(cfg, paths, index)
    if not fallback:
        print(f"\nnormalized {total} skills across {len(by_source)} source(s)")
    print(f"index      {paths['index']} ({index['skill_count']} skills)")
    print(f"manifests  {library['source_count']} source(s), {library['total_skills']} skills -> {paths['manifests']}")


def cmd_route(args, cfg, paths):
    if not paths["index"].exists():
        sys.exit("index not found — run `python -m scripts.skilllib build` first")
    top_k = args.top_k or cfg["router"].get("top_k", 5)
    hits, index = route(args.query, paths["index"], top_k=top_k)
    template = (PROMPTS_DIR / "route.md").read_text(encoding="utf-8")
    print(render_route(args.query, hits, top_k, template))


def cmd_export(args, cfg, paths):
    missing = [str(p) for p in (paths["index"], paths["manifests"] / "library.json")
               if not p.exists()]
    if missing:
        sys.exit("index/manifests not found — run `python -m scripts.skilllib build` first\n"
                 "  missing: " + ", ".join(missing))
    bundle_data, bundle_path, prompt_path = bundle.export_bundle(
        cfg, paths, args.curated_dir, Path(args.out))
    print(f"bundle: {bundle_path}")
    print(f"  {bundle_data['curated_count']} curated + {bundle_data['library_count']} library skills")
    print(f"prompt: {prompt_path}")


def cmd_import(args, cfg, paths):
    result = bundle.import_bundle(args.bundle, Path(args.curated_dir), paths)
    print(f"restored {result['curated']} curated + {result['normalized']} library skills "
          f"from {args.bundle}")
    print("index and manifests were restored from the bundle; `build` is optional "
          "(it regenerates identical files from the restored tree)")


def cmd_stats(args, cfg, paths):
    if not paths["index"].exists():
        sys.exit("index not found — run `python -m scripts.skilllib build` first")
    index = json.loads(paths["index"].read_text(encoding="utf-8"))
    skills = index.get("skills", [])
    by_source = {}
    for s in skills:
        by_source[s["source"]] = by_source.get(s["source"], 0) + 1
    print(f"skills: {index.get('skill_count', len(skills))}")
    print(f"sources: {len(by_source)}")
    for src, n in sorted(by_source.items(), key=lambda kv: -kv[1]):
        print(f"  {src:28s} {n:4d}")
    hashes = {}
    for s in skills:
        if s.get("hash"):
            hashes.setdefault(s["hash"], []).append(s["id"])
    dups = {h: ids for h, ids in hashes.items() if len(ids) > 1}
    if dups:
        print(f"\nduplicate bodies (identical sha256, dedup candidates):")
        for ids in sorted(dups.values(), key=len, reverse=True):
            print(f"  {' | '.join(ids)}")
    else:
        print("\nno duplicate skill bodies")
    print(f"index: {paths['index']}")


def cmd_ollama(args, cfg, paths):
    from agent.ollama_client import ollama_tags
    host = cfg.get("agent", {}).get("host", "http://localhost:11434")
    try:
        models = ollama_tags(host)
    except Exception as exc:
        sys.exit(f"cannot reach Ollama at {host} — is the server running?\n  {exc}")
    print(f"Ollama is running at {host}. Local models:")
    for m in models:
        print(f"  {m}")


def cmd_agent(args, cfg, paths):
    if not paths["index"].exists():
        sys.exit("index not found — run `python -m scripts.skilllib build` first")
    from agent.solver import solve
    print(f"routing: {args.query!r}")
    print("asking the local model — this can take a minute on CPU...")
    try:
        response, used, info = solve(args.query, cfg, paths, top_k=args.top_k)
    except Exception as exc:
        sys.exit(f"agent failed: {exc}")
    print("skills used:", ", ".join(used) if used else "(none matched — answered from base knowledge)")
    print(f"mode: {info['tier']} — think {'on' if info['think'] else 'off'}, "
          f"{info['max_tokens']} tok cap")
    print("-" * 60)
    print(response)


def cmd_chat(args, cfg, paths):
    """Interactive REPL: re-route every turn, keep a rolling conversation."""
    if not paths["index"].exists():
        sys.exit("index not found — run `python -m scripts.skilllib build` first")
    from agent.solver import solve
    history = []
    print("skill-aware chat with the local model (Ctrl-D to exit)")
    print("  /skills <query>  preview routing   /clear  reset conversation")
    print("=" * 60)
    while True:
        try:
            line = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line in ("/exit", "/quit", "/q"):
            break
        if line == "/clear":
            history.clear()
            print("(conversation cleared)")
            continue
        if line.startswith("/skills"):
            query = line[len("/skills"):].strip() or "latest request"
            top_k = args.top_k or cfg["router"].get("top_k", 5)
            hits, _ = route(query, paths["index"], top_k=top_k)
            names = ", ".join(h["name"] for h in hits) or "(none)"
            print(f"top matches: {names}")
            continue
        if line.startswith("/"):
            print(f"unknown command: {line}")
            continue
        print("thinking (CPU inference — can take a minute)...")
        try:
            response, used, info = solve(line, cfg, paths, top_k=args.top_k,
                                         history=history)
        except Exception as exc:
            print(f"error: {exc}")
            continue
        print(f"\n[skills used: {', '.join(used) if used else 'none'}]")
        print(f"[mode: {info['tier']} — think {'on' if info['think'] else 'off'}, "
              f"{info['max_tokens']} tok cap]")
        print("-" * 60)
        print(response)
        history.append(("user", line))
        history.append(("assistant", response))


def cmd_modelfile(args, cfg, paths):
    from agent.modelfile import render_modelfile
    system_text = (ROOT / "prompts" / "agent-system.md").read_text(encoding="utf-8")
    agent_cfg = cfg.get("agent", {})
    text = render_modelfile(
        system_text,
        model=agent_cfg.get("model", "qwen3:4b"),
        temperature=agent_cfg.get("temperature", 0.2),
        num_ctx=agent_cfg.get("num_ctx", 32768),
    )
    out = Path(args.out)
    out.write_text(text, encoding="utf-8")
    print(f"Modelfile written: {out}")
    print(f"build it with: ollama create {agent_cfg.get('model_tag', 'azmath-agent')} -f {out}")


def build_parser():
    p = argparse.ArgumentParser(prog="skilllib", description="Skill library CLI")
    p.add_argument("--config", default=str(DEFAULT_CONFIG), help="path to library.toml")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("sync", help="clone/update upstream sources")
    s.add_argument("--all", action="store_true", help="sync every configured source")
    s.set_defaults(func=cmd_sync)

    b = sub.add_parser("build", help="normalize + index + manifests")
    b.set_defaults(func=cmd_build)

    r = sub.add_parser("route", help="route a task query to matching skills")
    r.add_argument("query", help="the task description to route")
    r.add_argument("-k", "--top-k", type=int, default=None, help="number of hits")
    r.set_defaults(func=cmd_route)

    st = sub.add_parser("stats", help="index summary")
    st.set_defaults(func=cmd_stats)

    ex = sub.add_parser("export", help="write a portable bundle + prompt pack")
    ex.add_argument("-o", "--out", default=str(EXPORT_DIR), help="output directory")
    ex.add_argument("--curated-dir", default=str(CURATED_DIR),
                    help="curated .agents/skills directory")
    ex.set_defaults(func=cmd_export)

    im = sub.add_parser("import", help="restore the library from a bundle (offline)")
    im.add_argument("bundle", help="path to skills-bundle.json")
    im.add_argument("--curated-dir", default=str(CURATED_DIR),
                    help="curated .agents/skills directory")
    im.set_defaults(func=cmd_import)

    ol = sub.add_parser("ollama", help="show local Ollama server + model status")
    ol.set_defaults(func=cmd_ollama)

    ag = sub.add_parser("agent", help="route a task and answer with the local model")
    ag.add_argument("query", help="the task to solve")
    ag.add_argument("-k", "--top-k", type=int, default=None,
                    help="number of skills to inject (default: config max_skills)")
    ag.set_defaults(func=cmd_agent)

    ch = sub.add_parser("chat", help="interactive REPL: re-route every turn, keep context")
    ch.add_argument("-k", "--top-k", type=int, default=None,
                    help="number of skills to inject (default: config max_skills)")
    ch.set_defaults(func=cmd_chat)

    mf = sub.add_parser("modelfile", help="render the agent Modelfile")
    mf.add_argument("-o", "--out", default="Modelfile", help="output path")
    mf.set_defaults(func=cmd_modelfile)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    cfg = load_library_config(args.config)
    paths = library_paths(cfg)
    args.func(args, cfg, paths)


if __name__ == "__main__":
    main()
