# claude-code-discord

Claude Code Discord is an alternative to [Claude Code in Slack](https://code.claude.com/docs/en/slack). Anthropic shipped that Slack setup, I liked how it worked, and I wanted the same thing in Discord.

This repo keeps one Claude Code session running on a Linux server and connects it to Discord through the official [Discord channel plugin](https://github.com/anthropics/claude-plugins-official). Only your Discord account can talk to it.

On a server the bot answers when you:

- write the word `claude`,
- mention it (`@bot`),
- start a message with `!claude` (the default pattern already matches that),
- or reply to one of its messages.

The trigger only calls it in. The rest of the message is the request. If `claude` just comes up while you are talking to someone else, it stays out of the conversation and at most leaves a reaction.

A direct message from you always gets through.

## Install

Tested on Debian and Ubuntu. You need `sudo`, a Claude account, and a Discord bot token.

### 1. Discord bot

1. In the [Discord Developer Portal](https://discord.com/developers/applications), create an application and add a bot.
2. Turn on the **Message Content** privileged intent. Discord only forwards the text of a message when this is on, so the word `claude` can reach the bot.
3. Copy the bot token.
4. Invite the bot to your server with the **bot** scope and permission to view channels, send messages, read message history, and add reactions.

### 2. This repo

```bash
git clone https://github.com/c-airr/claude-code-discord.git
cd claude-code-discord
./install.sh
```

`install.sh` is safe to run again. It installs `tmux`, `unzip`, `python3`, `curl`, [Bun](https://bun.sh) (the Discord plugin runs on it), the Claude Code CLI, and `discord@claude-plugins-official`. It also installs three systemd units. The bot stays stopped until the last step.

### 3. Config

The installer copies `config.env.example` to `config.env` when that file is missing. Set your Discord user id:

```bash
# Discord: Settings → Advanced → Developer Mode,
# then right-click yourself → Copy User ID.
OWNER_ID=123456789012345678
```

The bot ignores every other account.

| Variable | Default | What it does |
|---|---|---|
| `GUILD_IDS` | empty | Comma-separated server ids. Empty means every server the bot has joined. |
| `PREFIX_PATTERN` | `\bclaude\b` | Case-insensitive regex that summons the bot, next to an @mention and a reply. |
| `MODEL` | `claude-sonnet-5-5` | Model alias or a full model id. |
| `IDLE_MINUTES` | `50` | After this much quiet time, compact the session when the context is large. |
| `COMPACT_MIN_TOKENS` | `40000` | Compact only above this context size. |

The token stays out of `config.env`. Put it in the plugin env file:

```bash
mkdir -p ~/.claude/channels/discord
printf 'DISCORD_BOT_TOKEN=your-token\n' > ~/.claude/channels/discord/.env
chmod 600 ~/.claude/channels/discord/.env
```

Optional files, all gitignored:

- `local.md`, copied from `local.example.md`. Notes for this machine only (language, host names, which account to use). They are appended to the system prompt.
- `settings.json`, copied from `settings.example.json` when you want your own permissions or hooks. Otherwise the example is used as-is.
- `~/.config/claude-discord/secrets.env`. Extra environment for tools inside the session, for example `GITHUB_PERSONAL_ACCESS_TOKEN`.

### 4. Log in once

Claude Code has to trust this directory and have a login on this machine:

```bash
claude
```

Run `/login`, then exit.

### 5. Start

```bash
./install.sh --start
```

That enables and starts:

- `claude-discord`, the session in tmux. systemd brings it back if it exits.
- `claude-discord-sync.timer`, every 5 minutes. It refreshes the channel allowlist and compacts the session after a long idle stretch.
- `claude-discord-restart.timer`, a fresh session every day at 05:00 in the server timezone.

```bash
systemctl status claude-discord
tmux attach -t claude          # watch the session; detach with Ctrl-b d
sudo systemctl restart claude-discord
```

In Discord, "reset", "new conversation", or "restart" does that same restart. It is back in about 20 seconds.

---

## Po polsku

Claude Code Discord to alternatywa dla [Claude Code w Slacku](https://code.claude.com/docs/en/slack). Anthropic zrobił takie rozwiązanie, spodobało mi się, więc przeniosłem je na Discorda.

To cienka warstwa nad Claude Code i oficjalną [wtyczką kanału Discord](https://github.com/anthropics/claude-plugins-official). Jedna sesja chodzi non stop na serwerze Linux i odpisuje przez tę wtyczkę. Rozmawiać z nią może tylko Twoje konto na Discordzie.

Na serwerze bot odzywa się, gdy:

- napiszesz słowo `claude`,
- oznaczysz go (`@bot`),
- zaczniesz wiadomość od `!claude` (domyślny wzorzec już to łapie),
- albo odpowiesz na jego wiadomość.

Słowo wywołujące tylko go przywołuje. Reszta wiadomości jest właściwą prośbą. Gdy `claude` padnie mimochodem w rozmowie z kimś innym, bot się nie wtrąca. Najwyżej zostawi reakcję.

Wiadomość prywatna od Ciebie zawsze do niego dociera.

## Instalacja

Sprawdzone na Debianie i Ubuntu. Potrzebny jest `sudo`, konto Claude i token bota Discord.

### 1. Bot na Discordzie

1. W [Discord Developer Portal](https://discord.com/developers/applications) utwórz aplikację i dodaj bota.
2. Włącz uprzywilejowany intent **Message Content**. Dopiero wtedy Discord przekazuje treść wiadomości, więc słowo `claude` w ogóle do bota dociera.
3. Skopiuj token bota.
4. Zaproś bota na serwer ze scopem **bot** i uprawnieniami do oglądania kanałów, wysyłania wiadomości, czytania historii i dodawania reakcji.

### 2. To repozytorium

```bash
git clone https://github.com/c-airr/claude-code-discord.git
cd claude-code-discord
./install.sh
```

`install.sh` można odpalać ponownie. Instaluje `tmux`, `unzip`, `python3`, `curl`, [Buna](https://bun.sh) (na nim chodzi wtyczka Discord), CLI Claude Code oraz `discord@claude-plugins-official`. Dopisuje też trzy unity systemd. Bot jeszcze nie startuje.

### 3. Konfiguracja

Instalator kopiuje `config.env.example` do `config.env`, jeśli tego pliku nie ma. Wpisz swoje id użytkownika Discord:

```bash
# Discord: Ustawienia → Zaawansowane → Tryb dewelopera,
# potem prawy przycisk na sobie → Kopiuj identyfikator użytkownika.
OWNER_ID=123456789012345678
```

Każde inne konto jest ignorowane.

| Zmienna | Domyślnie | Po co |
|---|---|---|
| `GUILD_IDS` | puste | Id serwerów po przecinku. Puste oznacza każdy serwer, na którym bot już jest. |
| `PREFIX_PATTERN` | `\bclaude\b` | Wyrażenie regularne (bez względu na wielkość liter), które przywołuje bota obok oznaczenia i odpowiedzi na jego wiadomość. |
| `MODEL` | `claude-sonnet-5-5` | Alias modelu albo pełne id. |
| `IDLE_MINUTES` | `50` | Po tylu minutach ciszy sesja jest kompaktowana, gdy kontekst jest duży. |
| `COMPACT_MIN_TOKENS` | `40000` | Kompaktowanie dopiero powyżej tego rozmiaru kontekstu. |

Token trzymasz poza `config.env`, w pliku środowiska wtyczki:

```bash
mkdir -p ~/.claude/channels/discord
printf 'DISCORD_BOT_TOKEN=twoj-token\n' > ~/.claude/channels/discord/.env
chmod 600 ~/.claude/channels/discord/.env
```

Opcjonalnie, wszystko w `.gitignore`:

- `local.md`, skopiowany z `local.example.md`. Notatki tylko dla tej instalacji (język, nazwy maszyn, które konto wybrać). Doklejają się do promptu systemowego.
- `settings.json`, skopiowany z `settings.example.json`, gdy chcesz własne uprawnienia albo hooki. Inaczej używany jest przykład.
- `~/.config/claude-discord/secrets.env`. Dodatkowe zmienne dla narzędzi w sesji, na przykład `GITHUB_PERSONAL_ACCESS_TOKEN`.

### 4. Jedno logowanie

Claude Code musi zaufać temu katalogowi i być zalogowany na tej maszynie:

```bash
claude
```

Wpisz `/login` i wyjdź.

### 5. Start

```bash
./install.sh --start
```

To włącza i uruchamia:

- `claude-discord`, sesję w tmux. systemd podnosi ją ponownie, gdy padnie.
- `claude-discord-sync.timer`, co 5 minut. Odświeża listę kanałów i kompaktuje sesję po dłuższej ciszy.
- `claude-discord-restart.timer`, świeżą sesję codziennie o 05:00 w strefie czasowej serwera.

```bash
systemctl status claude-discord
tmux attach -t claude          # podgląd sesji; odłączenie: Ctrl-b d
sudo systemctl restart claude-discord
```

Na Discordzie „reset”, „new conversation” albo „restart” robi ten sam restart. Wraca po około 20 sekundach.
