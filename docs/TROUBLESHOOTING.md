# Troubleshooting

First run `azmath doctor` — it checks Python, Ollama, model availability,
git, network, workspace writability, the skill index, tool registration, and
config, with actionable FAIL messages.

## Common issues

### "model returned an empty response"
The thinking trace consumed the entire token budget before the answer. Raise
`max_tokens` in `config/agent.toml` (the default 3200 was tuned for this
machine; a 1600 cap was measured to starve answers on tool prompts).

### It's slow (~3-11 min per run)
This is honest CPU inference with qwen3:4b (≈4 tok/s on an i5 with 16K
context). Mitigations:
- Small tasks get the 200-token simple tier automatically (`hello` ≈ 60s).
- Lower `num_ctx` (fewer tokens to generate around), or switch to a faster
  model via `AZMATH_MODEL_NAME`.
- Raise `max_tokens` only when answers come back empty.

### "cannot reach Ollama at ..."
Start the server (`ollama serve`), verify `ollama list` shows `qwen3:4b`,
then `azmath doctor` again.

### Destructive operations are blocked
That's the design. Non-interactive runs deny approval-level calls. To allow
(read the security implications first): `AZMATH_APPROVAL_MODE=allow`, or
narrow the pattern in `config/permissions.toml`.

### Web tools report "capability unavailable"
Offline, or the stdlib DuckDuckGo provider is blocked. Check network with
`azmath doctor`. A different backend can be injected via `build_runtime(web_provider=...)`.

### The loop hits the iteration cap
The task genuinely needed more steps, or the model kept emitting tool calls.
Raise `--iterations N` for `run`, or tighten the task description. The cap
exists so a runaway model can't loop forever.

### Where are the logs?
`~/.azmath/events.jsonl` — structured events per run (task, tools, denials,
durations). `AZMATH_LOG_LEVEL=debug` for verbose tracing. Secrets are
redacted.
