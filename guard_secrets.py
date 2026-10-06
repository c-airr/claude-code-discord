#!/usr/bin/env python3
"""PreToolUse hook: hard block on private keys leaving the machine.

The rule in prompt.md is only a request to the model - this hook enforces it even
if the model gets talked into it (e.g. prompt injection from an email or a web page).
It blocks:
- sending the body of a private key through any tool (Discord, Gmail, web...),
- attachments/paths pointing at ~/.ssh/id_*, *.pem, *.ppk,
- in Bash: printing keys (cat/head/base64...) and shipping them out
  (curl/wget/nc/mail/gist). scp/rsync/ssh between machines still work.
Exit code 2 = Claude Code rejects the call and shows the model the reason from stderr.
"""
import json
import re
import sys

KEY_BODY = re.compile(r"PRIVATE KEY-----|PuTTY-User-Key-File|OPENSSH PRIVATE KEY")
# private key file: ~/.ssh/id_xxx (not .pub), *.pem, *.ppk
KEY_FILE = re.compile(r"\.ssh/id_[A-Za-z0-9_-]+(?!\.pub)\b|\.ppk\b|\.pem\b|\.ssh/[^\s'\"]*key(?!\.pub)\b")
LEAKY_CMD = re.compile(r"\b(cat|less|more|head|tail|base64|xxd|od|strings|curl|wget|nc|ncat|socat|mail|sendmail|mutt|gist|python3?|node|bun)\b")
COPY_CMD = re.compile(r"^\s*(sudo\s+)?(scp|rsync|ssh-copy-id|install|cp|chmod|chown|ssh-keygen\s+-[lyf])\b")


def block(reason: str) -> None:
    print(f"BLOCKED by guard_secrets: {reason}. Private keys never leave the machines "
          "(they may only be copied between the owner's machines with scp/rsync).", file=sys.stderr)
    sys.exit(2)


def main() -> None:
    event = json.load(sys.stdin)
    tool = event.get("tool_name", "")
    data = event.get("tool_input", {})
    blob = json.dumps(data, ensure_ascii=False)

    if KEY_BODY.search(blob):
        block(f"{tool} contains a private key")

    if tool == "Bash":
        cmd = data.get("command", "")
        for part in re.split(r"&&|\|\||;|\|", cmd):
            if KEY_FILE.search(part) and LEAKY_CMD.search(part) and not COPY_CMD.match(part):
                block("the command reads or sends a private key file")
        return

    if tool == "Read":
        if KEY_FILE.search(data.get("file_path", "")):
            block("reading a private key file")
        return

    # Discord/Gmail/web: attachments and paths pointing at keys
    if KEY_FILE.search(blob):
        block(f"{tool} references a private key file")


if __name__ == "__main__":
    main()
