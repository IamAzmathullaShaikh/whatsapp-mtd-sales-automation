"""azmath — command-line interface for the local agent platform.

    azmath                          interactive chat
    azmath run "<task>"             one-shot agent run
    azmath skills list|search|stats|sync|build
    azmath tools list [--schemas]
    azmath models list
    azmath doctor
    azmath config [show]
    azmath version
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from azmath import __version__
from azmath.core.config import ROOT, load_settings
from azmath.runtime import build_runtime

VERSION = __version__


def _print_progress(line: str) -> None:
    print(f"  {line}", flush=True)


# -- commands ----------------------------------------------------------------

def cmd_version(args, rt):
    print(f"azmath {VERSION}")
    print(f"python {sys.version.split()[0]}")
    print(f"config: {rt.settings.source}")


def cmd_config(args, rt):
    import json
    print(json.dumps(rt.settings._data, indent=2, default=str))


def cmd_models(args, rt):
    names = rt.providers.list()
    print("model providers:", ", ".join(names))
    print()
    for name in names:
        p = rt.providers.get(name)
        ok = "OK" if p.health() else "FAIL"
        print(f"[{ok}] {name}: {p.model} @ {p.host}")
        if not ok:
            print("      start Ollama (`ollama serve`) and pull the model, or set AZMATH_MODEL_NAME")


def cmd_tools(args, rt):
    names = rt.registry.list()
    print(f"{len(names)} tools registered; enabled: {len(rt.registry.enabled())}")
    for name in names:
        tool = rt.registry.get(name)
        state = "on " if rt.registry.is_enabled(name) else "off"
        print(f"  [{state}] {name:<14} {tool.permission.value:<9} {tool.description}")
        if args.schemas:
            import json
            print("        " + json.dumps(tool.schema(), default=str))


def cmd_doctor(args, rt):
    checks = []
    checks.append(("python >= 3.11", sys.version_info >= (3, 11), sys.version.split()[0]))
    checks.append(("azmath imports", True, "core modules import cleanly"))
    checks.append(("config loads", True, rt.settings.source))
    checks.append(("tools registered", len(rt.registry.list()) > 0,
                   f"{len(rt.registry.list())} tools"))
    checks.append(("skill index", rt.skills is not None,
                   "skills/index/index.json" if rt.skills else "index missing — run `azmath skills build`"))
    try:
        models = rt.provider.models()
        ok = rt.provider.model in models
        checks.append(("ollama reachable", ok,
                       f"{len(models)} local models" if ok else
                       f"model {rt.provider.model!r} not installed (ollama pull {rt.provider.model})"))
    except Exception as exc:
        checks.append(("ollama reachable", False, f"unreachable: {exc} (start `ollama serve`)"))
    import shutil
    git_bin = shutil.which("git")
    checks.append(("git available", bool(git_bin), git_bin or "git not on PATH"))
    probe = rt.workspace.root / ".azmath_write_probe"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        checks.append(("workspace writable", True, str(rt.workspace.root)))
    except OSError as exc:
        checks.append(("workspace writable", False, f"cannot write: {exc}"))
    net_ok = False
    try:
        import urllib.request
        urllib.request.urlopen("https://api.github.com", timeout=5)
        net_ok = True
    except Exception:
        net_ok = False
    checks.append(("network", net_ok, "github reachable" if net_ok else "offline (web tools will report unavailable)"))

    failed = 0
    for name, ok, detail in checks:
        print(f"[{'OK' if ok else 'FAIL'}] {name}: {detail}")
        failed += 0 if ok else 1
    print()
    if failed:
        print(f"{failed} check(s) failed — see the FAIL lines above for the fix.")
        return 1
    print("all checks passed")
    return 0


def cmd_run(args, rt):
    if not args.task:
        sys.exit("azmath run: a task is required (quote it)")
    result = rt.make_loop(progress=_print_progress).run(
        args.task, max_iterations=args.iterations, dry_run=args.dry_run)
    print("-" * 60)
    print(result.response)
    print("-" * 60)
    print(f"status: {result.status} | iterations: {result.iterations} | "
          f"{result.duration:.1f}s | skills: {', '.join(result.used_skills) or 'none'}")
    if result.verification is not None:
        print(result.verification.summary())
    if result.status == "tool_limit":
        print("hit the iteration cap — the task may need more steps (--iterations N)")
    if result.error:
        print(f"error: {result.error}")
    _maybe_save_memory(rt, result, args)
    return 0 if result.ok else 1


def _maybe_save_memory(rt, result, args):
    if not rt.memory.available or not result.ok:
        return
    approved = bool(rt.settings.memory_cfg.get("persist_without_approval")) or args.save
    if approved is False and sys.stdin.isatty() and not args.yes:
        try:
            answer = input(f"save this task to long-term memory? [y/N] ").strip().lower()
            approved = answer in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            approved = False
    if approved:
        saved = rt.memory.remember(
            f"task-{result.tool_calls[0]['id'] if result.tool_calls else 'noop'}",
            result.response, {"task": result.task[:200]}, approved=True)
        print("saved to long-term memory" if saved else "(long-term memory disabled)")


def cmd_chat(args, rt):
    print(f"azmath {VERSION} — interactive. Ctrl-D to exit. /help for commands.")
    history = []
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
        if line in ("/help", "/h"):
            print("  /skills <q>  preview routing   /clear  reset context   /exit  quit")
            continue
        if line == "/clear":
            history.clear()
            print("(context cleared)")
            continue
        if line.startswith("/skills"):
            q = line[len("/skills"):].strip() or "latest request"
            if rt.skills:
                hits = rt.skills.resolve(q)
                print("skills:", ", ".join(h["name"] for h in hits) or "(none)")
            else:
                print("skill index unavailable")
            continue
        loop = rt.make_loop(progress=_print_progress)
        result = loop.run(line, history=history, task_id=f"chat-{len(history) // 2}")
        print("-" * 60)
        print(result.response)
        print("-" * 60)
        if result.verification is not None:
            print(result.verification.summary())
        history.append(("user", line))
        history.append(("assistant", result.response))


def cmd_skills(args, rt):
    if args.action == "stats":
        if not rt.skills:
            sys.exit("skill index missing — run `azmath skills build`")
        from azmath.skills import SkillRegistry
        reg = SkillRegistry(ROOT / "skills" / "index" / "index.json")
        print(f"skills: {reg.count()}")
        for source, n in reg.by_source():
            print(f"  {source:28s} {n:4d}")
        return
    if args.action == "list":
        from azmath.skills import SkillRegistry
        reg = SkillRegistry(ROOT / "skills" / "index" / "index.json")
        for s in reg.skills():
            print(f"{s.get('name'):<40s} {s.get('source'):<22s} {str(s.get('description', ''))[:80]}")
        return
    if args.action == "search":
        from azmath.skills import SkillRegistry
        reg = SkillRegistry(ROOT / "skills" / "index" / "index.json")
        for s in reg.search(args.query, top_k=10):
            print(f"{s.get('name'):<40s} {s.get('source'):<22s} {str(s.get('description', ''))[:80]}")
        return
    if args.action in ("sync", "build"):
        _delegate_skilllib(args.action)
        return
    sys.exit(f"unknown skills action: {args.action}")


def _delegate_skilllib(action: str) -> None:
    """Reuse the proven skilllib pipeline for sync/build (idempotent)."""
    from scripts import skilllib
    from scripts.common import DEFAULT_CONFIG, load_library_config, library_paths
    cfg = load_library_config(DEFAULT_CONFIG)
    paths = library_paths(cfg)
    if action == "sync":
        import argparse as _ap
        skilllib.cmd_sync(_ap.Namespace(all=False), cfg, paths)
    else:
        skilllib.cmd_build(argparse.Namespace(), cfg, paths)


# -- parser ------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="azmath", description="Local autonomous agent platform")
    p.add_argument("--config", default=None, help="path to agent.toml")
    p.add_argument("--workspace", default=None, help="workspace root for file tools")
    sub = p.add_subparsers(dest="command")

    sub.add_parser("version", help="version information").set_defaults(func=cmd_version)
    sub.add_parser("config", help="show effective configuration").set_defaults(func=cmd_config)
    m = sub.add_parser("models", help="list model providers and health")
    m.add_argument("action", nargs="?", choices=["list"], default="list",
                   help="subcommand (only 'list' today)")
    m.set_defaults(func=cmd_models)
    t = sub.add_parser("tools", help="list registered tools")
    t.add_argument("action", nargs="?", choices=["list"], default="list",
                   help="subcommand (only 'list' today)")
    t.add_argument("--schemas", action="store_true", help="print full schemas")
    t.set_defaults(func=cmd_tools)
    sub.add_parser("doctor", help="environment self-diagnostics").set_defaults(func=cmd_doctor)

    r = sub.add_parser("run", help="run the agent on a task")
    r.add_argument("task", help="the task to perform (quote it)")
    r.add_argument("-i", "--iterations", type=int, default=None, help="iteration cap")
    r.add_argument("--dry-run", action="store_true", help="show tool calls without executing")
    r.add_argument("--save", action="store_true", help="save to long-term memory without asking")
    r.add_argument("-y", "--yes", action="store_true", help="never prompt for approval")
    r.set_defaults(func=cmd_run)

    sub.add_parser("chat", help="interactive chat with the agent").set_defaults(func=cmd_chat)

    sk = sub.add_parser("skills", help="skill library operations")
    sk.add_argument("action", choices=["stats", "list", "search", "sync", "build"])
    sk.add_argument("query", nargs="?", help="search query")
    sk.set_defaults(func=cmd_skills)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if not getattr(args, "func", None):
        build_parser().print_help()
        return 0
    settings = load_settings()
    if args.config:
        settings = load_settings(Path(args.config))
    if args.command == "version":
        rt = type("RT", (), {"settings": settings})()  # lightweight for version
    else:
        rt = build_runtime(settings, workspace=args.workspace)
    try:
        return int(args.func(args, rt) or 0)
    except KeyboardInterrupt:
        print("\n(interrupted)")
        return 130


if __name__ == "__main__":
    sys.exit(main())
