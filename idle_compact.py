#!/usr/bin/env python3
"""Sends /compact to the bot session after the owner has been away for a while.

Every message resends the whole context, and after a break the prompt cache has
expired anyway - so after IDLE_MINUTES without activity we shrink the conversation
to a summary. Runs from a systemd timer every 5 minutes. The session is identified
by run/session_id (start.sh passes it via --session-id); state comes from the transcript:
- context size = usage of the last model response,
- a compact_boundary after it means it is already compacted - nothing to do.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_DIR = Path.home() / ".claude/projects" / str(HERE).replace("/", "-")


def load_env(path: Path) -> dict:
    env = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip("'\"")
    return env


def context_state(transcript: Path) -> tuple[int, bool]:
    """(context tokens after the last response, compacted since then?)"""
    tokens, compacted = 0, False
    for line in transcript.open(encoding="utf-8"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") == "assistant":
            u = d.get("message", {}).get("usage") or {}
            tokens = (u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0)
                      + u.get("cache_creation_input_tokens", 0))
            compacted = False
        elif d.get("type") == "system" and d.get("subtype") == "compact_boundary":
            compacted = True
    return tokens, compacted


def main() -> int:
    cfg = load_env(HERE / "config.env")
    idle_min = int(cfg.get("IDLE_MINUTES", "50"))
    min_tokens = int(cfg.get("COMPACT_MIN_TOKENS", "40000"))

    sid_file = HERE / "run" / "session_id"
    if not sid_file.exists():
        return 0
    transcript = PROJECT_DIR / f"{sid_file.read_text().strip()}.jsonl"
    if not transcript.exists():
        return 0

    idle = (time.time() - transcript.stat().st_mtime) / 60
    tokens, compacted = context_state(transcript)
    if compacted or idle < idle_min or tokens < min_tokens:
        return 0

    print(f"idle {idle:.0f} min, context {tokens} tokens -> /compact")
    subprocess.run(["tmux", "send-keys", "-t", "claude", "-l", "/compact"], check=True)
    time.sleep(1)
    subprocess.run(["tmux", "send-keys", "-t", "claude", "Enter"], check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
