#!/usr/bin/env python3
"""Claude plan usage on Discord: a reset ping with a video, and the numbers in the bot's status.

Runs every minute from a systemd timer. Reads the 5-hour and weekly limits of the Claude
account this server is logged into (the same endpoint Claude Code's /usage uses, with its
OAuth token) and:
- when a remembered reset time passes, posts limits_reset.mp4 to the first channel in
  LIMITS_CHANNELS that accepts it, pinging OWNER_ID ("bro, claude limits reset (5h)");
- writes "5h 71% · 1w 12%" to run/limits-status.txt, which the patched plugin shows as the
  bot's custom status (patch_plugin.py: limits-status).

The usage endpoint is internal and rate limited, so it is called every 5 minutes only.
Reset times are known in advance, so the ping still comes on time (even with an expired token).
Standard library + curl only.
"""
import json
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from sync_channels import STATE_DIR, load_env

HERE = Path(__file__).resolve().parent
STATE = HERE / "run" / "limits-state.json"
STATUS = HERE / "run" / "limits-status.txt"
VIDEO = HERE / "limits_reset.mp4"
CREDS = Path.home() / ".claude" / ".credentials.json"
NAMES = {"five_hour": "5h", "seven_day": "1w"}


def fetch_usage() -> dict:
    tok = json.loads(CREDS.read_text())["claudeAiOauth"]["accessToken"]
    req = urllib.request.Request("https://api.anthropic.com/api/oauth/usage", headers={
        "Authorization": f"Bearer {tok}", "anthropic-beta": "oauth-2025-04-20"})
    return json.load(urllib.request.urlopen(req, timeout=30))


def send(token: str, channels: list[str], owner: str, text: str) -> bool:
    payload = json.dumps({"content": f"<@{owner}> {text}", "allowed_mentions": {"users": [owner]}})
    for ch in channels:
        r = subprocess.run(["curl", "-sf", "-o", "/dev/null", "-H", f"Authorization: Bot {token}",
                            "-F", f"payload_json={payload}", "-F", f"files[0]=@{VIDEO}",
                            f"https://discord.com/api/v10/channels/{ch}/messages"])
        if r.returncode == 0:
            return True
        print(f"posting to {ch} failed (curl {r.returncode})", file=sys.stderr)
    return False


def main() -> None:
    cfg = load_env(HERE / "config.env")
    token = load_env(STATE_DIR / ".env").get("DISCORD_BOT_TOKEN")
    channels = [c for c in cfg.get("LIMITS_CHANNELS", "").split(",") if c.strip()]
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    now = datetime.now(timezone.utc)

    # resets that already passed; a failed post stays in state and is retried next minute
    for key, when in list(state.items()):
        if datetime.fromisoformat(when) <= now:
            if not channels or send(token, channels, cfg["OWNER_ID"], f"bro, claude limits reset ({NAMES[key]})"):
                del state[key]

    if not state or now.minute % 5 == 0:
        try:
            usage = fetch_usage()
        except Exception as e:
            print(f"usage API: {e}", file=sys.stderr)
        else:
            for key in NAMES:
                when = (usage.get(key) or {}).get("resets_at")
                # never overwrite a passed reset whose post failed - it is still waiting for a retry
                if when and datetime.fromisoformat(when) > now and not (key in state and datetime.fromisoformat(state[key]) <= now):
                    state[key] = when
            STATUS.parent.mkdir(exist_ok=True)
            STATUS.write_text(" · ".join(
                f"{NAMES[k]} {(usage.get(k) or {}).get('utilization') or 0:.0f}%" for k in NAMES))

    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state))


if __name__ == "__main__":
    main()
