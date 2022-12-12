# miniirc_discord

[![Available on PyPI.](https://img.shields.io/pypi/v/miniirc-discord.svg)](https://pypi.org/project/miniirc-discord/)

A wrapper for miniirc ([GitHub], [GitLab]) to allow bots or clients made in
miniirc to connect to (proprietary) [Discord] servers via [discord.py] with
minimal code changes.

## How to use

To use miniirc_discord, you already need to know how to use miniirc ([GitHub],
[GitLab]). Instead of creating a `miniirc.IRC` object, however, you need to
use `miniirc_discord.Discord`. This is very similar, however has some
differences:

 - `miniirc_discord.Discord` objects are created with
   `miniirc_discord.Discord('TOKEN')`.
 - There is a [`stateless_mode` keyword argument](#stateless-mode).
 - The `discord_client` attribute returns an instance of `discord.Client`, or
    `None` if stateless_mode is enabled.
 - There is a `get_server_count()` method which returns the number of guilds
    the bot is in.

Channels will start in `#` if they are public and are currently just a channel
ID.

Some formatting from IRC to Discord should be translated nicely, however
more complex codes and formatting from Discord to IRC are currently not.

Your bot will need to be able to request the "message content" intent for
miniirc_discord to work properly.

### Stateless mode

The `stateless_mode` keyword argument will instruct discord.py to disable the
user cache and any intents not required by miniirc_discord. This should be
enabled if you are not using `discord_client` to cut back on memory and
bandwidth usage.

Since miniirc_discord 0.6.0, the stateless_mode keyword argument is `True` by
default.

### Example

```py
TOKEN = os.environ['DISCORD_TOKEN']

irc = miniirc_discord.Discord(TOKEN)
channel = irc.discord_client.get_channel(channel_id)  # Error!

# Disabling stateless mode will add a "discord_client" attribute
irc = miniirc_discord.Discord(TOKEN, stateless_mode=False)
channel = irc.discord_client.get_channel(channel_id)  # No error
```

## Supported commands

### `PRIVMSG`

`PRIVMSG` operates like you'd expect and IRC formatting codes are converted to
markdown. You can use the `+draft/reply` IRCv3 tag to reply to a message.

### `CTCP ACTION` (`irc.me()`)

This works similarly to `PRIVMSG`, except the CTCP ACTION is also converted to
a Discord `/me`.

### `NOTICE`

`NOTICE`s are converted into embeds by miniirc_discord. To set an embed title,
you can add a bold line to the start of the embed:

```py
irc.notice(channel, '\x02Embed title\x02\nEmbed content')
```

You can add an
[IRC colour code](https://modern.ircdocs.horse/formatting.html#colors)
to the start of the line to set the embed colour:

```py
# Green embed
irc.notice(channel, '\x033\x02Embed title\x02\x03\nEmbed content')

# Light blue embed
irc.notice(channel, '\x0312\x02Embed title\x02\x03\nEmbed content')
```

Older versions of miniirc_discord had a non-standard IRCv3 tag to set the embed
title. This is still supported, however you should switch to the above syntax
when possible.

### `TAGMSG`

You can add reactions to messages using the `+draft/react` message tag.

Example:

```py
@irc.Handler('PRIVMSG', colon=False, ircv3=True)
def handle_privmsg(irc, hostmask, tags, args):
    if args[1] == '$react':
        irc.send('TAGMSG', args[0], tags={
            '+draft/reply': tags.get('msgid'),
            '+draft/react': '🆗️'
        })
```

### `AWAY`

`AWAY` will set the bot's "Playing" text. If you
want to change the prefix to something else, you can set the non-standard IRCv3
client tag `+discordapp.com/type` to (`Playing`, `Streaming`, `Listening to` or
`Watching`). The `+discordapp.com/status` tag can be set to `'online'`,
`'idle'`, `'dnd'` or `'invisible'`.

## Installation and setting up

You can install `miniirc_discord` with `pip`. On Linux-based systems, you would
do `sudo pip3 install miniirc_discord`. Version numbers should follow SemVer
since 0.4.0 and are no longer in sync with `miniirc`.

## Getting a bot token

To get a Discord bot token and invite link, see [this guide]. Make sure you
enable the message content intent in the bot settings page.

[GitHub]:       https://github.com/luk3yx/miniirc
[GitLab]:       https://gitlab.com/luk3yx/miniirc
[Discord]:      https://discord.com
[discord.py]:   https://github.com/Rapptz/discord.py
[this guide]:   https://github.com/reactiflux/discord-irc/wiki/Creating-a-discord-bot-&-getting-a-token
