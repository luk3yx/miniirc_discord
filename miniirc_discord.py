#!/usr/bin/python3
#
# miniirc_discord: Allows miniirc bots/clients to connect to Discord.
# Attempts to use IRCv3 tags to allow reactions etc to be sent.
#
# Licensed under the MIT License:
# https://gitlab.com/luk3yx/miniirc_discord/LICENSE.md
#

import asyncio, discord, miniirc, re, time

ver      = (0,5,0)
version  = '0.5.0'
__all__  = ['Discord', 'miniirc']
channels = {}

def _hostmask(author):
    return (
        author.mention,
        author.name,
        'discord/{}/<@{}>'.format('bot' if author.bot else 'user', author.id)
    )

@asyncio.coroutine
def _handle_privmsg(irc, message):
    if irc._client.user == message.author:
        return

    # Create miniirc-style objects
    irc.debug('New message:', message)
    hostmask = _hostmask(message.author)

    # Create the tags
    tags = {
        'draft/msgid':  message.id,
        'server-time':  message.timestamp.strftime('%Y-%m-%dT%H:%M:%SZ'),
    }

    # Create the args
    channel = message.channel.id
    if not message.channel.is_private:
        channel = '#' + channel
    channels[channel] = message.channel
    args = [channel, ':' + message.content]

    irc.debug('Handling message:', hostmask, tags, args)
    irc._handle('PRIVMSG', hostmask, tags, args)

formats = {
    '\x1f': '__',
    '\x1d': '*',
    '\x02': '**',
}
_strip_colours = re.compile('\x03[0-9]?[0-9]?')
def _irc_to_discord(msg):
    msg = _strip_colours.sub('', msg)
    msg = msg.replace('\\', '\\\\').replace('_', '\\_').replace('*', '\\*')
    for format in formats:
        msg = msg.replace(format + format, '').replace(format, formats[format])
    return msg

# Register outgoing commands
_outgoing_cmds = {}
def _register_cmd(*cmds):
    def x(func):
        for cmd in cmds:
            cmd = str(cmd).upper()
            _outgoing_cmds[cmd] = func
        return func
    return x

# PRIVMSG
@_register_cmd('PRIVMSG')
def _on_privmsg(self, client, run, tags, cmd, args):
    if len(args) == 2 and args[0] in channels:
        chan = channels[args[0]]
        msg  = args[-1][1:]
        if msg[:7].upper() == '\x01ACTION':
            msg = '\x1d' + msg[8:].replace('\x01', '') + '\x1d'
        msg = _irc_to_discord(msg)
        self.debug('Translated PRIVMSG:', msg)
        run(client.send_message(chan, msg))
    else:
        self.debug('Invalid call to PRIVMSG.')

# IRC colour hex values
_colours = [
    0xffffff,   # 0.  White
    0x000000,   # 1.  Black
    0x0000ff,   # 2.  Blue
    0x00ff00,   # 3.  Green
    0xff0000,   # 4.  Red
    0xd2691e,   # 5.  Brown
    0xff00ff,   # 6.  Purple
    0xff8800,   # 7.  Orange
    0xffff00,   # 8.  Yellow
    0x88ff88,   # 9.  Light green
    # TODO: Add more and allow them to be used in NOTICE
]

# NOTICE
@_register_cmd('NOTICE')
def _on_notice(self, client, run, tags, cmd, args):
    if len(args) != 2 or args[0] not in channels:
        return self.debug('Invalid call to NOTICE.')
    title = tags.get('+discordapp.com/embed-title') or ''
    msg = args[1][1:]
    colour = None
    if msg.startswith('\x03') and len(msg) > 2:
        try:
            colour = _colours[int(msg[1])]
        except:
            pass
    title, msg = _irc_to_discord(title), _irc_to_discord(msg)
    embed = discord.Embed(title = title or None, description = msg,
        colour = colour or discord.Embed.Empty)
    run(client.send_message(channels[args[0]], embed = embed))

# AWAY
@_register_cmd('AWAY')
def _on_away(self, client, run, tags, cmd, args):
    game = ' '.join(args)
    if game.startswith(':'):
        game = game[1:]
    ptype = (tags and tags.get('+discordapp.com/type') or '').lower()
    url   = None
    if ptype == 'watching':
        ptype = 3
    elif ptype == 'listening to':
        ptype = 2
    elif ptype == 'streaming':
        ptype = 1
        url  = 'https://www.twitch.tv/directory'
    else:
        ptype = 0
    game = discord.Game(name = game, type = ptype, url = url)
    self.debug('Changing online presence:', game)
    run(client.change_presence(game = game))

# NAMES
@_register_command('NAMES')
def _on_names(self, client, run, tags, cmd, args):
    run(client.send_messge(chan, discord.Server.members))

# The discord class
class Discord(miniirc.IRC):
    _client = None

    def _run(self, coroutine):
        return asyncio.run_coroutine_threadsafe(coroutine, self._client.loop)

    def quote(self, *msg, force = None, tags = None):
        # Parse the message using miniirc's built-in parser to reduce redundancy
        msg = ' '.join(msg)
        self.debug('>>>', msg)
        cmd, hostmask, _, args = miniirc.ircv3_message_parser(msg)
        cmd = cmd.upper()
        del _

        if type(tags) != dict:
            tags = {}

        if _outgoing_cmds.get(cmd):
            _outgoing_cmds[cmd](self, self._client, self._run, tags, cmd, args)
        else:
            self.debug('Unknown command run:', cmd)

    def _main(self):
        self.debug('Main loop running!')

        self._client.run(self.ip)
        self.connected = False
        self.debug('Disconnected!')

        if self.persist:
            self.debug('Reconnecting in 5 seconds...')

    def connect(self):
        if self.connected:
            self.debug('Already connected!')
            return
        self.connected = True
        self.debug('Connecting...')

        self._client = discord.Client()
        @self._client.async_event
        def on_message(message):
            yield from _handle_privmsg(self, message)

        self.main()

    def disconnect(self):
        raise NotImplementedError

    def get_server_count(self):
        if not self._client:
            return 0
        return len(self._client.servers)

# Add get_server_count equivalent to IRC.
miniirc.IRC.get_server_count = lambda irc : 1 if irc.connected else 0
