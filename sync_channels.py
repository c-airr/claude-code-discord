#!/usr/bin/env python3
"""Keeps the discord plugin's access.json in sync with the server's channel list.

The plugin only lets messages through from channels listed one by one in `groups`
(keyed by channel ID), but we want the whole server. This script fetches every
text channel with the bot token and writes them into access.json - the plugin
re-reads that file on every message, so no restart is needed. It also opens the
DM channel with the owner and stores its ID (used to send sensitive things privately).

Standard library only - runs from a systemd timer every few minutes.
"""
import json
import os
import sys
import tempfile
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATE_DIR = Path(os.environ.get("DISCORD_STATE_DIR", Path.home() / ".claude/channels/discord"))
ACCESS_FILE = STATE_DIR / "access.json"
DM_FILE = HERE / "run" / "dm_channel_id"
API = "https://discord.com/api/v10"

# channel types you can talk in: text, voice (text-in-voice), announcement, forum, media
TEXT_TYPES = {0, 2, 5, 15, 16}


def load_env(path: Path) -> dict:
    env = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip("'\"")
    return env


def api(token: str, method: str, path: str, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method, headers={
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
        "User-Agent": "claude-code-discord (https://github.com/c-airr/claude-code-discord, 1.0)",
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".")
    with os.fdopen(fd, "w") as f:
        f.write(text)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def main() -> int:
    cfg = load_env(HERE / "config.env")
    token = os.environ.get("DISCORD_BOT_TOKEN") or load_env(STATE_DIR / ".env").get("DISCORD_BOT_TOKEN")
    owner = cfg.get("OWNER_ID", "")
    guild_ids = [g.strip() for g in cfg.get("GUILD_IDS", "").split(",") if g.strip()]
    if not token or not owner:
        print("missing DISCORD_BOT_TOKEN or OWNER_ID", file=sys.stderr)
        return 1

    if not guild_ids:
        guild_ids = [g["id"] for g in api(token, "GET", "/users/@me/guilds")]

    channels = []
    for gid in guild_ids:
        channels += [c["id"] for c in api(token, "GET", f"/guilds/{gid}/channels")
                     if c["type"] in TEXT_TYPES]

    access = json.loads(ACCESS_FILE.read_text()) if ACCESS_FILE.exists() else {}
    access["dmPolicy"] = "allowlist"
    access["allowFrom"] = [owner]
    access["pending"] = {}
    access["mentionPatterns"] = [cfg.get("PREFIX_PATTERN", r"\bclaude\b")]
    access.setdefault("ackReaction", "👀")
    # server channels: owner only, and only when summoned (mention / pattern / reply to the bot)
    access["groups"] = {cid: {"requireMention": True, "allowFrom": [owner]} for cid in channels}

    new = json.dumps(access, indent=2, ensure_ascii=False) + "\n"
    if not ACCESS_FILE.exists() or ACCESS_FILE.read_text() != new:
        write_atomic(ACCESS_FILE, new)
        print(f"access.json: {len(channels)} channels from {len(guild_ids)} server(s)")

    if not DM_FILE.exists():
        dm = api(token, "POST", "/users/@me/channels", {"recipient_id": owner})
        write_atomic(DM_FILE, dm["id"] + "\n")
        print(f"DM channel with the owner: {dm['id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
