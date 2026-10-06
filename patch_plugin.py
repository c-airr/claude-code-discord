#!/usr/bin/env python3
"""Patch the official discord plugin (server.ts) in place. Run by start.sh.

Idempotent: every patch leaves a `[cc-discord:<name>]` marker and is skipped when the
marker is already there. If a plugin update changes the code a patch anchors on, the
patch is skipped with a warning instead of breaking the bot.

Patches:
- dm-fetch: replies look the channel up in the discord.js cache, and a DM channel that
  arrived as a "partial" has no recipientId there, so replying to the owner's DM fails
  with "not allowlisted". Force a fresh fetch.
- perm-in-chat: permission prompts (Allow/Deny buttons) go to the channel of the
  owner's last message instead of DM, so they show up where the conversation is.
  "See more" in a server channel answers ephemerally (only the owner sees the tool
  input). Falls back to DM if the channel send fails.
- approve-reaction: when someone replies to a bot message and an allowlisted user
  reacts to that reply with ✅, the reply is delivered to Claude (meta
  `approved_by`, `in_reply_to`), even though its author is not allowlisted.
"""
import glob
import os
import re
import sys

PATCHES = [
    ("dm-fetch", [
        (re.compile(r"await client\.channels\.fetch\(id\)$", re.M),
         "await client.channels.fetch(id, { force: true }) // [cc-discord:dm-fetch]"),
    ]),
    ("perm-in-chat", [
        # remember where the owner talks to us
        ("  const chat_id = msg.channelId\n",
         "  const chat_id = msg.channelId\n  lastChatId = chat_id // [cc-discord:perm-in-chat]\n"),
        ("const pendingPermissions = new Map",
         "let lastChatId: string | undefined\nconst pendingPermissions = new Map"),
        # send the prompt to that channel, DM as a fallback
        ("""    for (const userId of access.allowFrom) {
      void (async () => {
        try {
          const user = await client.users.fetch(userId)
          await user.send({ content: text, components: [row] })""",
         """    if (lastChatId) {
      try {
        const ch = await client.channels.fetch(lastChatId, { force: true })
        if (ch && 'send' in ch) {
          await ch.send({ content: text, components: [row] })
          return
        }
      } catch (e) {
        process.stderr.write(`permission_request send to channel ${lastChatId} failed: ${e}\\n`)
      }
    }
    for (const userId of access.allowFrom) {
      void (async () => {
        try {
          const user = await client.users.fetch(userId)
          await user.send({ content: text, components: [row] })"""),
        # "See more" in a server channel: only the owner sees the details
        ("    await interaction.update({ content: expanded, components: [row] }).catch(() => {})",
         """    if (interaction.inGuild()) {
      await interaction.reply({ content: expanded.slice(0, 1900), ephemeral: true }).catch(() => {})
      return
    }
    await interaction.update({ content: expanded, components: [row] }).catch(() => {})"""),
    ]),
    ("approve-reaction", [
        ("    GatewayIntentBits.MessageContent,\n  ],",
         "    GatewayIntentBits.MessageContent,\n    GatewayIntentBits.GuildMessageReactions, // [cc-discord:approve-reaction]\n  ],"),
        ("  partials: [Partials.Channel],",
         "  partials: [Partials.Channel, Partials.Message, Partials.Reaction, Partials.User],"),
        ("client.once('ready', c => {",
         """const approvedIds = new Set<string>()
client.on('messageReactionAdd', async (reaction, user) => {
  try {
    if (reaction.emoji.name !== '✅' || user.bot) return
    const access = loadAccess()
    if (!access.allowFrom.includes(user.id)) return
    const msg = reaction.message.partial ? await reaction.message.fetch() : reaction.message
    if (msg.author.bot || approvedIds.has(msg.id) || !msg.reference?.messageId) return
    const channelId = msg.channel.isThread() ? msg.channel.parentId ?? msg.channelId : msg.channelId
    if (msg.guildId && !access.groups[channelId]) return
    const ref = await msg.fetchReference()
    if (ref.author.id !== client.user?.id) return
    approvedIds.add(msg.id)
    void msg.react(access.ackReaction ?? '👀').catch(() => {})
    await mcp.notification({
      method: 'notifications/claude/channel',
      params: {
        content: msg.content || '(attachment)',
        meta: {
          chat_id: msg.channelId,
          message_id: msg.id,
          user: msg.author.username,
          user_id: msg.author.id,
          ts: msg.createdAt.toISOString(),
          approved_by: user.id,
          in_reply_to: ref.id,
          in_reply_to_text: ref.content.slice(0, 300),
        },
      },
    })
  } catch (e) {
    process.stderr.write(`discord: approve-reaction failed: ${e}\\n`)
  }
})

client.once('ready', c => {"""),
    ]),
]


def apply(src: str, name: str, edits) -> str:
    if f"[cc-discord:{name}]" in src:
        return src
    if name == "dm-fetch" and "fetch(id, { force: true })" in src:  # older sed-based fix
        return src
    out = src
    for old, new in edits:
        if isinstance(old, re.Pattern):
            out, n = old.subn(new, out)
        else:
            n = out.count(old)
            out = out.replace(old, new, 1)
        if n == 0:
            print(f"patch_plugin: '{name}' skipped - anchor not found (plugin changed?)", file=sys.stderr)
            return src
    return out


def main() -> None:
    pattern = os.path.expanduser("~/.claude/plugins/cache/claude-plugins-official/discord/*/server.ts")
    for path in glob.glob(pattern):
        src = open(path, encoding="utf-8").read()
        new = src
        for name, edits in PATCHES:
            new = apply(new, name, edits)
        if new != src:
            open(path, "w", encoding="utf-8").write(new)
            print(f"patch_plugin: patched {path}")


if __name__ == "__main__":
    main()
