#!/usr/bin/env bash
# One-time setup on a Linux server (Debian/Ubuntu tested). Safe to re-run.
#   ./install.sh            install deps, plugin and systemd units (does not start the bot)
#   ./install.sh --start    same, then enable and start everything
set -euo pipefail
cd "$(dirname "$0")"
DIR="$PWD"
TZ_NAME="${TZ_NAME:-$(timedatectl show -p Timezone --value 2>/dev/null || echo UTC)}"
export PATH="$HOME/.local/bin:$HOME/.bun/bin:$PATH"

step() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }

step "System packages (tmux, unzip, python3)"
sudo apt-get install -y -qq tmux unzip python3 curl >/dev/null

step "Bun (the discord plugin runs on it)"
command -v bun >/dev/null || curl -fsSL https://bun.sh/install | bash

step "Claude Code"
command -v claude >/dev/null || curl -fsSL https://claude.ai/install.sh | bash
claude --version

step "Discord channel plugin"
claude plugin marketplace add anthropics/claude-plugins-official >/dev/null 2>&1 || true
claude plugin install discord@claude-plugins-official --scope user

step "Config files"
[ -f config.env ] || { cp config.env.example config.env; echo "created config.env - fill in OWNER_ID"; }
mkdir -p "$HOME/.claude/channels/discord"
[ -f "$HOME/.claude/channels/discord/.env" ] || echo "!! put DISCORD_BOT_TOKEN=... into ~/.claude/channels/discord/.env (chmod 600)"
chmod +x ./*.sh ./*.py

step "systemd units (user=$USER, dir=$DIR, restart timezone=$TZ_NAME)"
for f in systemd/*; do
    sed -e "s#@USER@#$USER#g" -e "s#@DIR@#$DIR#g" -e "s#@TZ@#$TZ_NAME#g" "$f" \
        | sudo tee "/etc/systemd/system/$(basename "$f")" >/dev/null
done
sudo systemctl daemon-reload

if [ "${1:-}" = "--start" ]; then
    step "Starting"
    sudo systemctl enable --now claude-discord claude-discord-sync.timer claude-discord-restart.timer
    systemctl --no-pager status claude-discord | head -5
else
    cat <<EOF

Next steps:
  1. Fill in config.env (OWNER_ID) and the bot token (see README).
  2. Log in once and trust this folder:  cd $DIR && claude   (then /login, exit)
  3. ./install.sh --start
EOF
fi
