"""Render an Ollama Modelfile for the skill-aware agent personality.

Single source of truth for the system prompt is prompts/agent-system.md;
the Modelfile inlines it so `ollama create <name> -f Modelfile` yields a
model you can also chat with interactively.
"""

MODELFILE_TEMPLATE = """FROM {model}

PARAMETER temperature {temperature}
PARAMETER num_ctx {num_ctx}

SYSTEM \"\"\"
{system_text}\"\"\"
"""


def render_modelfile(system_text, model="qwen3:4b", temperature=0.2, num_ctx=32768):
    return MODELFILE_TEMPLATE.format(
        model=model, temperature=temperature, num_ctx=num_ctx,
        system_text=system_text.strip())
