#!/usr/bin/env python3
"""PreToolUse hook for Agent: subagents are only allowed for the `-opus` flag.

The main session runs on a cheaper model; a message with `-opus` is handed to a
subagent with model "opus" (the alias always points at the newest Opus). Any other
Agent call - different model, no model (= inherit) - is rejected, so the session
does not burn usage on subagents nobody asked for.
Exit code 2 = Claude Code rejects the call and shows the model the reason from stderr.
"""
import json
import sys


def main() -> None:
    event = json.load(sys.stdin)
    if event.get("tool_name") != "Agent":
        return
    if event.get("tool_input", {}).get("model") != "opus":
        print("BLOCKED by guard_agent: subagents are only for the -opus flag "
              "and must use model \"opus\". Do the task yourself.", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
