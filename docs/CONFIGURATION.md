# Configuration

Configuration is centralized — no scattered environment variables. Two TOML
files (stdlib `tomllib`, no YAML dependency):

- `config/agent.toml` — platform: model, loop, tools, memory, observability.
- `config/permissions.toml` — permission policy (see TOOLS.md).

## config/agent.toml

```toml
[model]
provider = "ollama"        # only "ollama" today — plug others into azmath/models
name = "qwen3:4b"
host = "http://localhost:11434"
temperature = 0.2
num_ctx = 16384            # measured ceiling on this 14 GB CPU box (32k = swap)
max_tokens = 3200          # complex tier; 1600 starved the answer on tool prompts
simple_max_tokens = 200    # greetings/small talk: fast + concise
think = "auto"             # "auto" | true | false (auto classifies per query)
timeout = 300              # seconds per model call (idle timeout; streaming resets it)

[loop]
max_iterations = 8         # runtime-owned termination
tool_timeout = 60
verify = true              # verification stage before finishing
max_obs_chars = 8000       # context budget for tool observations

[tools]
enabled = ["fs", "shell", "git", "web", "python"]   # name prefixes; empty = all
approval_mode = "prompt"   # prompt | deny | allow

[memory]
backend = "json"
path = "~/.azmath/memory.json"
persist_without_approval = false   # persistence is opt-in per run

[observability]
log_level = "info"
events_file = "~/.azmath/events.jsonl"   # "" disables the JSONL trace
```

## Environment overrides

Every key has an `AZMATH_<SECTION>_<KEY>` override (see
`ENV_OVERRIDES` in `azmath/core/config/settings.py`). Examples:

```bash
AZMATH_MODEL_NAME=qwen3:8b        # switch model without editing files
AZMATH_MAX_ITERATIONS=3           # tighten the loop for CI
AZMATH_APPROVAL_MODE=deny         # never approve destructive ops (CI)
AZMATH_VERIFY=false               # skip verification
AZMATH_LOG_LEVEL=debug            # full event trace
```

CLI flags: `--config <path>` picks a different agent.toml;
`--workspace <dir>` sets the filesystem tools' root (default: repo root).

`azmath config` prints the effective merged configuration.
