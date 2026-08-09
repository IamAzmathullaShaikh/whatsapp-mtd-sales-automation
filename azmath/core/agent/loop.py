"""The agent loop: plan -> execute -> observe -> re-evaluate -> verify.

The runtime owns termination (iteration cap, timeouts, retry); the model never
decides when the loop ends. Tool choice is the model's, driven by the schemas
in the prompt — there are no hard-coded task branches anywhere.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from azmath.core.context import ContextManager
from azmath.core.events import EventBus
from azmath.core.memory import MemoryStore
from azmath.tools import ApprovalHandler, Policy, ToolRegistry

from .executor import ToolExecutor
from .observer import Observer
from .planner import build_system_prompt, parse_tool_call
from .verifier import Verifier


@dataclass
class RunResult:
    task: str
    response: str
    status: str          # completed | tool_limit | error
    used_skills: list[str] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    iterations: int = 0
    duration: float = 0.0
    verification: object | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == "completed"


class AgentLoop:
    def __init__(self, provider, registry: ToolRegistry, policy: Policy,
                 approver: ApprovalHandler, *, settings=None,
                 context: ContextManager | None = None, verifier: Verifier | None = None,
                 skills_loader=None, memory: MemoryStore | None = None,
                 bus: EventBus | None = None, progress=None,
                 personality: str | None = None,
                 max_obs_chars: int | None = None):
        self.provider = provider
        self.registry = registry
        self.policy = policy
        self.approver = approver
        self.settings = settings
        self.loop_cfg = (settings.loop if settings else {}) or {}
        self.context = context or ContextManager(
            max_obs_chars=max_obs_chars or self.loop_cfg.get("max_obs_chars", 8000))
        self.verifier = verifier or Verifier()
        self.skills_loader = skills_loader
        self.memory = memory
        self.bus = bus or EventBus()
        self.progress = progress or (lambda line: None)
        self.personality = personality
        self.executor = ToolExecutor(registry, policy, approver)

    # -- public --------------------------------------------------------------
    def run(self, task: str, *, history=None, max_iterations: int | None = None,
            dry_run: bool = False, task_id: str | None = None) -> RunResult:
        task_id = task_id or uuid.uuid4().hex[:12]
        started = time.monotonic()
        max_iter = max_iterations or int(self.loop_cfg.get("max_iterations", 8))
        observer = Observer()
        self.bus.emit("task.started", task_id=task_id, task=task[:200],
                      model=getattr(self.provider, "model", self.provider.name))

        skills = self.skills_loader.resolve(task) if self.skills_loader else []
        used = [s["name"] for s in skills]
        self.progress(f"skills: {', '.join(used) if used else 'none matched'}")

        system = build_system_prompt(self.personality or self._default_personality())
        observations: list[str] = []
        response = ""
        status = "error"

        for i in range(1, max_iter + 1):
            prompt = self.context.build_prompt(
                task=task, system=system,
                tool_schemas=self.registry.schemas(),
                skills=skills, history=history, observations=observations)
            self.progress(f"model call {i}/{max_iter} ...")
            try:
                response = self.provider.generate(prompt, system=system)
            except Exception as exc:
                return self._finish(task, "", "error", used, observer, started,
                                    task_id, error=f"model call failed: {exc}")
            if not response.strip():
                # an empty generation is a failure, never a silent completion
                return self._finish(task, "", "error", used, observer, started,
                                    task_id, error="model returned an empty response")
            call = parse_tool_call(response)
            if call is None:
                status = "completed"
                break
            self.progress(f"tool: {call['tool']} {call['args']}")
            outcome = self.executor.execute(call["tool"], call["args"], dry_run=dry_run)
            result = outcome["result"]
            obs = observer.record(
                tool=call["tool"], args=call["args"], ok=result.ok,
                output=result.output, error=result.error,
                duration=result.duration, level=outcome["level"].value,
                reason=outcome["reason"], dry_run=result.dry_run)
            observations.append(obs)
            self.bus.emit(
                "tool.called" if outcome["allowed"] else "tool.denied",
                task_id=task_id, tool=call["tool"],
                ok=result.ok, level=outcome["level"].value,
                duration=result.duration)
        else:
            # loop exhausted without a final answer
            status = "tool_limit"
            self.progress(f"stopped: iteration limit {max_iter} reached")

        return self._finish(task, response, status, used, observer, started,
                            task_id, error=None)

    # -- internals -----------------------------------------------------------
    def _finish(self, task, response, status, used, observer, started, task_id, error):
        verification = None
        if status == "completed" and self.loop_cfg.get("verify", True):
            verification = self.verifier.verify(task, observer, response)
            self.progress(verification.summary())
        duration = time.monotonic() - started
        self.bus.emit("task.finished", task_id=task_id, status=status,
                      iterations=len(observer.calls), duration=round(duration, 3))
        if self.memory:
            self.memory.session.set("last_task", task)
            self.memory.session.set("last_response", response)
            self.memory.session.set("last_status", status)
        return RunResult(task=task, response=response.strip(), status=status,
                         used_skills=used, tool_calls=list(observer.calls),
                         iterations=len(observer.calls), duration=duration,
                         verification=verification, error=error)

    def _default_personality(self) -> str:
        from azmath.core.config import ROOT
        path = ROOT / "prompts" / "agent-system.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return "You are Azmath Agent, a local AI assistant."
