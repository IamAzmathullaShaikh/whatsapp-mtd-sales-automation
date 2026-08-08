"""Skill-aware agent: route a request, load the best skills, ask the local model.

The model stays small and static — the capability surface grows by injecting
the *selected* skills (not the whole library) into each request.
"""

from pathlib import Path

from router.router import route
from scripts.common import ROOT, load_library_config, library_paths

from scripts.common import CURATED_DIR

from .ollama_client import OllamaUnavailable, ollama_generate

PROMPTS_DIR = ROOT / "prompts"
DEFAULT_SYSTEM = PROMPTS_DIR / "agent-system.md"


def load_skill_excerpts(hits, paths, max_chars, curated_dir=None):
    """Excerpt each routed skill's body (first max_chars).

    Upstream skills come from skills/normalized/<source__>/<name>/body.md;
    curated project skills (source 'curated/local') from
    <curated_dir>/<name>/SKILL.md.
    """
    excerpts = []
    for h in hits:
        if h.get("source") == "curated/local":
            if not curated_dir:
                continue
            body_path = Path(curated_dir) / h.get("name", "") / "SKILL.md"
        else:
            source_dir = h.get("source", "").replace("/", "__")
            body_path = paths["normalized"] / source_dir / h.get("name", "") / "body.md"
        if not body_path.exists():
            continue
        body = body_path.read_text(encoding="utf-8", errors="replace")
        excerpts.append({
            "name": h.get("name", ""),
            "source": h.get("source", ""),
            "description": str(h.get("description", ""))[:400],
            "body_excerpt": body[:max_chars],
        })
    return excerpts


def trim_history(history, max_turns=6):
    """Keep only the last `max_turns` exchanges (each exchange is two entries)."""
    if not history or max_turns <= 0:
        return []
    return history[-2 * max_turns:]


def compose_chat_prompt(skills, history, user_request):
    """The task prompt: plain conversation history, then the current turn's
    selected skills, then the user request.

    History carries only the user/assistant exchanges (never the injected skill
    excerpts) so the rolling context stays small; skills are re-routed and
    injected fresh every turn.
    """
    parts = []
    if history:
        parts.append("## Conversation so far")
        parts.append("")
        for role, text in history:
            parts.append(f"{role}: {text}")
        parts.append("")
    if skills:
        parts.append("## Selected skills (follow their instructions when relevant)")
        parts.append("")
        for s in skills:
            parts.append(f"### skill: {s['name']} [{s['source']}]")
            parts.append(f"**When to use:** {s['description']}")
            parts.append("")
            parts.append(s["body_excerpt"])
            parts.append("")
    parts.append("## User task")
    parts.append("")
    parts.append(user_request)
    return "\n".join(parts)


def compose_task_prompt(skills, user_request):
    """Single-shot task prompt (no history) — same shape as chat, minus context."""
    return compose_chat_prompt(skills, None, user_request)


SIMPLE_TIER_PHRASES = (
    "hello there", "hi there", "hey there", "good morning", "good afternoon",
    "good evening", "good night", "how are you", "what's up", "whats up",
    "who are you", "what can you do", "nice to meet you",
)


def classify_complexity(query):
    """'simple' for greetings/small talk, else 'complex'.

    Conservative on purpose: anything that is not clearly small talk gets the
    full reasoning budget, so a short technical question is never starved.
    """
    q = " ".join(str(query).lower().split())
    if not q:
        return "complex"
    if q in ("hello", "hi", "hey", "yo", "ok", "okay", "bye", "goodbye"):
        return "simple"
    if "thank" in q or any(p in q for p in SIMPLE_TIER_PHRASES):
        return "simple"
    return "complex"


def solve(user_request, cfg=None, paths=None, *, top_k=None, max_skill_chars=None,
          model=None, host=None, temperature=None, num_ctx=None, think=None,
          system_path=DEFAULT_SYSTEM, history=None, max_history_turns=None):
    """Route the request, inject the best skills, and ask the local model.

    Returns (response, used, info) where info = {"tier", "think", "max_tokens"}.

    `think` accepts "auto" (default), True, or False. In "auto" mode the query
    is classified and a budget tier is chosen: greetings/small talk get a small
    token cap (fast, concise), everything else gets the full cap. `think` stays
    True in BOTH tiers — verified empirically on Ollama 0.32.6 that think=False
    makes qwen3 narrate its deliberation into the response (the leak), while the
    trace only ever lands in the separate `thinking` field our client ignores.

    `history` is a rolling list of (role, text) exchanges; only the last
    `max_history_turns` are kept, and each turn re-routes the current request
    against the skill index.
    """
    cfg = cfg or load_library_config()
    paths = paths or library_paths(cfg)
    agent_cfg = cfg.get("agent", {})
    top_k = top_k or agent_cfg.get("max_skills", 4)
    max_chars = max_skill_chars or agent_cfg.get("max_skill_chars", 2000)
    model = model or agent_cfg.get("model", "qwen3:4b")
    host = host or agent_cfg.get("host", "http://localhost:11434")

    hits, _ = route(user_request, paths["index"], top_k=top_k)
    skills = load_skill_excerpts(hits, paths, max_chars, curated_dir=CURATED_DIR)
    system = Path(system_path).read_text(encoding="utf-8")
    history = trim_history(history, max_history_turns or agent_cfg.get("max_history_turns", 6))
    prompt = compose_chat_prompt(skills, history, user_request)

    think_cfg = think if think is not None else agent_cfg.get("think", "auto")
    if think_cfg == "auto":
        tier = classify_complexity(user_request)
        effective_think = True  # never think=False: it leaks qwen3's narration
        max_tokens = agent_cfg.get(
            "simple_max_tokens" if tier == "simple" else "max_tokens", 1600)
    else:
        tier = "fixed"
        effective_think = bool(think_cfg)
        max_tokens = agent_cfg.get("max_tokens", 1600)

    response = ollama_generate(
        host, model, prompt,
        system=system,
        temperature=temperature if temperature is not None
        else agent_cfg.get("temperature", 0.2),
        num_ctx=num_ctx or agent_cfg.get("num_ctx", 16384),
        timeout=agent_cfg.get("timeout", 600),
        think=effective_think,
        max_tokens=max_tokens,
    )
    info = {"tier": tier, "think": effective_think, "max_tokens": max_tokens}
    return response, [s["name"] for s in skills], info
