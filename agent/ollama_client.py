"""Minimal Ollama REST client (stdlib only, no external dependencies)."""

import json
import urllib.error
import urllib.request


class OllamaUnavailable(Exception):
    """The Ollama server could not be reached."""


class OllamaError(Exception):
    """Ollama returned an explicit error for the request."""


def ollama_tags(host, timeout=5):
    """GET /api/tags -> sorted list of local model names."""
    with urllib.request.urlopen(f"{host.rstrip('/')}/api/tags", timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return sorted(m.get("name") for m in data.get("models", []))


def build_generate_payload(model, prompt, *, system=None, temperature=0.2,
                           num_ctx=16384, stream=False, think=None,
                           max_tokens=None):
    """Pure request-builder for POST /api/generate (testable)."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": stream,
        "options": {"temperature": temperature, "num_ctx": num_ctx},
    }
    if max_tokens:
        payload["options"]["num_predict"] = max_tokens
    if system:
        payload["system"] = system
    if think is not None:
        payload["think"] = think
    return payload


def ollama_generate(host, model, prompt, *, system=None, temperature=0.2,
                    num_ctx=16384, timeout=600, think=None, max_tokens=None):
    """POST /api/generate (streaming) -> the model's response text.

    Streaming matters on slow CPU-only boxes: tokens arrive incrementally, so
    progress flows and a hung model can't stall the socket silently.
    """
    payload = build_generate_payload(
        model, prompt, system=system, temperature=temperature,
        num_ctx=num_ctx, stream=True, think=think, max_tokens=max_tokens)
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{host.rstrip('/')}/api/generate", data=body,
        headers={"Content-Type": "application/json"})
    chunks = []
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            for raw in resp:
                line = raw.decode("utf-8").strip()
                if not line:
                    continue
                data = json.loads(line)
                chunks.append(data.get("response", ""))
                if data.get("done"):
                    break
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        # connect/read failures AND socket timeouts — both mean unreachable/slow
        raise OllamaUnavailable(
            f"cannot reach Ollama at {host} within {timeout}s: {exc}") from exc
    return "".join(chunks)
