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

Currently only `PRIVMSG`s (and `CTCP ACTION`s) are supported, however PRs are
welcome.

You can use `AWAY` to set the bot's "Playing" text. Running this
command with an empty value will unset it.

When you run `AWAY`, you can use the IRCv3 client tag `+discordapp.com/type`
and set it to one of the allowed case-insensitive prefixes (`Playing`,
`Streaming`, `Listening to` or `Watching`). Note that setting it to `Streaming`
will set the stream URL to a dummy page.


Some formatting from IRC to Discord should be translated nicely, however
more complex codes and formatting from Discord to IRC are currently not.

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
