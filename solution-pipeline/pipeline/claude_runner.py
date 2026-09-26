"""One headless Claude Code call (`claude -p`) for an agent defined in agents/*.md.

- The user's MCP connectors are switched off for the call (--strict-mcp-config with none), which
  saves ~23k tokens of tool definitions per call.
- The agent's system prompt replaces Claude Code's default one.
- A figure is attached to the message itself (stream-json input), so no file tool or extra turn.
- The answer comes back as JSON validated against a schema (--json-schema).
"""

import base64
import json
import re
import subprocess
import time
from pathlib import Path

from common import CONFIG

USAGE_LIMIT = re.compile(r"usage limit|rate limit|limit reached|resets at|out of (extra )?usage|429", re.I)


class UsageLimitReached(Exception):
    """The plan's usage limit is exhausted: stop the batch; the next run resumes."""


def call(agent: dict, prompt: str, schema: dict, workdir: Path, image: Path | None = None, model: str | None = None):
    model = model or agent["model"]
    cmd = ["claude", "-p", "--model", model, "--input-format", "stream-json", "--output-format", "stream-json",
           "--verbose", "--no-session-persistence", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
           "--system-prompt", agent["prompt"], "--json-schema", json.dumps(schema), "--tools", agent.get("tools", "")]
    if agent["allowed"]:
        cmd += ["--allowedTools", *agent["allowed"]]
    if CONFIG.get("effort"):
        cmd += ["--effort", CONFIG["effort"]]
    content = [{"type": "text", "text": prompt}]
    if image:
        media = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
                 ".webp": "image/webp"}.get(image.suffix.lower(), "image/png")
        content.insert(0, {"type": "image", "source": {"type": "base64", "media_type": media,
                                                       "data": base64.b64encode(image.read_bytes()).decode()}})
    message = json.dumps({"type": "user", "message": {"role": "user", "content": content}}) + "\n"
    started = time.time()
    proc = subprocess.run(cmd, input=message, capture_output=True, text=True, encoding="utf-8",
                          cwd=workdir, timeout=CONFIG["call_timeout_seconds"])
    seconds = round(time.time() - started, 1)
    result = None
    for line in proc.stdout.splitlines():
        if line.startswith("{"):
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "result":
                result = event
    if result is None:
        text = (proc.stderr or proc.stdout)[-800:]
        if USAGE_LIMIT.search(text):
            raise UsageLimitReached(text.strip())
        return None, {"model": model, "error": text, "seconds": seconds}
    if result.get("is_error") and USAGE_LIMIT.search(str(result.get("result", ""))):
        raise UsageLimitReached(str(result.get("result")))
    usage = result.get("usage", {})
    stats = {
        "model": model,
        "input": usage.get("input_tokens", 0), "cache_create": usage.get("cache_creation_input_tokens", 0),
        "cache_read": usage.get("cache_read_input_tokens", 0), "output": usage.get("output_tokens", 0),
        "thinking": (usage.get("output_tokens_details") or {}).get("thinking_tokens", 0),
        "api_cost_usd": result.get("total_cost_usd", 0), "turns": result.get("num_turns"), "seconds": seconds,
        "error": result.get("result") if result.get("is_error") else None,
    }
    return result.get("structured_output"), stats
