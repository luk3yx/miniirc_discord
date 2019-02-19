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

 - `ip` is now your Discord token (see [this guide] to get one).
 - `port`, `nick`, `ident` and `realname` are currently ignored, however still
    need to be the expected type (`port` should be `0` or `65536`).

Channels will start in `#` if they are public and are currently just a channel
ID. Before you can send messages into a channel, however, someone needs to send
a message in one of them.

Some formatting from IRC to Discord should be translated nicely, however
more complex codes and formatting from Discord to IRC are currently not.

## Supported commands

### `PRIVMSG`

`PRIVMSG` operates like you'd expect and IRC formatting codes are converted to
markdown. You cannot, however, send messages to a channel before the bot has
received a message from the channel.

### `CTCP ACTION` (`irc.me()`)

This works similarly to `PRIVMSG`, except the CTCP ACTION is also converted to
a Discord `/me`.

### `NOTICE`

*Before miniirc_discord 0.5.0, `NOTICE` is an alias for `PRIVMSG`.*

`NOTICE` adds nice embeds into Discord, while remaining as compatible as
possible with IRC. You can set the IRCv3 client tag `+discordapp.com/title` to
set the embed title (note that this will not be displayed on IRC), and add an
[IRC colour/color code](https://github.com/myano/jenni/wiki/IRC-String-Formatting#color-codes)
to the start of the line to set the embed colour/color. Only codes `0` to `9`
are currently supported, and using leading zeroes (`03` or `05`) will break.

### `AWAY`

Similar to `bitlbee-discord`, `AWAY` will set the bot's "Playing" text. If you
want to change the prefix to something else, you can set the IRCv3 client tag
`+discordapp.com/type` to (`Playing`, `Streaming`, `Listening to` or
`Watching`). The `+discordapp.com/status` tag can be set to `'online'`,
`'idle'`, `'dnd'` or `'invisible'`.

## Installation and setting up

You can install `miniirc_discord` with `pip`. On Linux-based systems, you would
do `sudo pip3 install miniirc_discord`. Version numbers should follow SemVer
since 0.4.0 and are no longer in sync with `miniirc` until `miniirc_discord`
becomes more stable.

### Manual installation

To install `miniirc_discord` manually, you can usually place it in the same
directory as your other `.py` files or in a package directory.

You will need to install the following dependencies (normally with `pip3`):
 - `discord.py`
 - `miniirc`

## Getting a bot token

To get a Discord bot token and invite link, see [this guide].

[GitHub]:       https://github.com/luk3yx/miniirc
[GitLab]:       https://gitlab.com/luk3yx/miniirc
[Discord]:      https://discordapp.com
[discord.py]:   https://github.com/Rapptz/discord.py
[this guide]:   https://github.com/reactiflux/discord-irc/wiki/Creating-a-discord-bot-&-getting-a-token
