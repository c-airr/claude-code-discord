#!/usr/bin/env bash
# Starts the Claude Code session with the Discord channel inside tmux.
# The session has to be interactive, and tmux lets you attach to it: `tmux attach -t claude`.
# systemd keeps this script in the foreground - it exits when the session dies.
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:$HOME/.bun/bin:$PATH"
# On a 1 GB box the bun plugin servers can take >30 s (the default MCP timeout) to start;
# Claude Code does not retry, so the bot would stay offline until the next restart.
export MCP_TIMEOUT=120000
set -a; . ./config.env; set +a

# Optional secrets for tools inside the session (kept out of the repo), e.g.
# GITHUB_PERSONAL_ACCESS_TOKEN for the `github` plugin - without it the plugin sends
# an empty "Bearer " header and GitHub answers 400.
SECRETS="$HOME/.config/claude-discord/secrets.env"
if [ -f "$SECRETS" ]; then
    set -a; . "$SECRETS"; set +a
    export GH_TOKEN="${GH_TOKEN:-${GITHUB_PERSONAL_ACCESS_TOKEN:-}}"
fi

python3 sync_channels.py
mkdir -p run

# DM bug fix, permission prompts in the chat, ✅-approved replies (see the file).
# Idempotent, and re-applied after plugin updates.
python3 patch_plugin.py

# Fixed session ID so idle_compact.py knows which transcript to watch.
cat /proc/sys/kernel/random/uuid > run/session_id

# Prompt = shared rules + optional local.md (your machines, accounts, language...).
cat prompt.md $( [ -f local.md ] && echo local.md ) \
    | sed -e "s/{{OWNER_ID}}/$OWNER_ID/g" -e "s/{{DM_CHANNEL_ID}}/$(cat run/dm_channel_id)/g" \
    > run/prompt.md

# Settings = your settings.json, or the example; @DIR@ points the hook at this directory.
SETTINGS=settings.json; [ -f "$SETTINGS" ] || SETTINGS=settings.example.json
sed "s#@DIR@#$PWD#g" "$SETTINGS" > run/settings.json

tmux kill-session -t claude 2>/dev/null || true
tmux new-session -d -s claude -x 200 -y 50 \
    claude --channels plugin:discord@claude-plugins-official \
           --model "$MODEL" \
           --session-id "$(cat run/session_id)" \
           --settings "$PWD/run/settings.json" \
           --append-system-prompt-file "$PWD/run/prompt.md"

while tmux has-session -t claude 2>/dev/null; do sleep 10; done
echo "claude session ended"
exit 1
