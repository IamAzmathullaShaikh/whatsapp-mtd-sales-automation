"""Runtime factory: assemble the whole platform from Settings via DI.

The CLI (and tests) build a Runtime once; nothing else constructs providers,
registries, or policies by hand.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from azmath.core.agent import AgentLoop
from azmath.core.config import ROOT, Settings, load_settings
from azmath.core.events import EventBus
from azmath.core.memory import JsonMemory, MemoryStore
from azmath.models import ProviderRegistry
from azmath.models.ollama import OllamaProvider
from azmath.tools import ApprovalHandler, Policy, ToolRegistry
from azmath.tools import build_default_registry
from azmath.tools.fs import Workspace
from azmath.skills import SkillResolver
from scripts.common import CURATED_DIR, library_paths, load_library_config


@dataclass
class Runtime:
    settings: Settings
    workspace: Workspace
    provider: object
    registry: ToolRegistry
    policy: Policy
    approver: ApprovalHandler
    bus: EventBus
    memory: MemoryStore
    skills: SkillResolver | None
    providers: ProviderRegistry = field(default_factory=ProviderRegistry)

    def make_loop(self, progress=None, verifier=None) -> AgentLoop:
        return AgentLoop(
            self.provider, self.registry, self.policy, self.approver,
            settings=self.settings, skills_loader=self.skills, memory=self.memory,
            bus=self.bus, progress=progress, verifier=verifier)


def build_runtime(settings: Settings | None = None, workspace: str | None = None,
                  web_provider=None, progress=None, input_fn=None,
                  enable_memory: bool = True) -> Runtime:
    settings = settings or load_settings()
    ws = Workspace(workspace or ROOT)

    provider = OllamaProvider(
        model=settings.model.get("name", "qwen3:4b"),
        host=settings.model.get("host", "http://localhost:11434"),
        temperature=settings.model.get("temperature", 0.2),
        num_ctx=settings.model.get("num_ctx", 16384),
        max_tokens=settings.model.get("max_tokens", 1600),
        simple_max_tokens=settings.model.get("simple_max_tokens", 200),
        think=settings.model.get("think", "auto"),
        timeout=settings.model.get("timeout", 300))

    providers = ProviderRegistry()
    providers.register(provider)

    registry = build_default_registry(settings, ws, web_provider)
    policy = Policy(settings.permissions)
    approver = ApprovalHandler(
        settings.tools_cfg.get("approval_mode", "prompt"), input_fn=input_fn)
    bus = EventBus(settings.observability.get("events_file", ""))
    memory_store = None
    if enable_memory:
        mem_path = settings.memory_cfg.get("path", "~/.azmath/memory.json")
        memory_store = MemoryStore(JsonMemory(settings.expand(mem_path)))

    skills = None
    try:
        lib_cfg = load_library_config()
        paths = library_paths(lib_cfg)
        agent_cfg = settings.section("model")
        skills = SkillResolver(
            paths["index"], paths,
            top_k=settings.get("model", "max_skills", 4) or lib_cfg["agent"].get("max_skills", 4),
            max_chars=lib_cfg["agent"].get("max_skill_chars", 2000),
            curated_dir=CURATED_DIR)
    except Exception:
        skills = None  # skills are optional; the agent still works without the index

    return Runtime(settings=settings, workspace=ws, provider=provider,
                   registry=registry, policy=policy, approver=approver,
                   bus=bus, memory=memory_store, skills=skills, providers=providers)
