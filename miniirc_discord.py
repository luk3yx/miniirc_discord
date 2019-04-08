#!/usr/bin/python3
#
# miniirc_discord: Allows miniirc bots/clients to connect to Discord.
# Attempts to use IRCv3 tags to allow reactions etc to be sent.
#
# Licensed under the MIT License:
# https://gitlab.com/luk3yx/miniirc_discord/LICENSE.md
#

import asyncio, discord, miniirc, re, time

ver      = (0,5,10)
version  = '0.5.10'
__all__  = ['Discord', 'miniirc']
channels = {}

def _hostmask(author):
    return (
        author.mention,
        '{}#{}'.format(author.name, author.discriminator),
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
    if hasattr(message, 'created_at'):
        ts = message.created_at
    else:
        ts = message.timestamp

    tags = {
        'draft/msgid':  str(message.id),
        'server-time':  ts.strftime('%Y-%m-%dT%H:%M:%SZ'),
    }

    # Create the args
    channel = str(message.channel.id)

    if hasattr(discord, 'abc'):
        is_pv = isinstance(message.channel, discord.abc.PrivateChannel)
    else:
        is_pv = message.is_private

    if not is_pv:
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
_escape_re     = re.compile(r'([_\*\\])')
_url_re        = re.compile(r'^\<?https?\:\/\/')
def _irc_to_discord(msg):
    msg = _strip_colours.sub('', msg)

    # TODO: A nicer more compact way of escaping values
    msg  = msg.split(' ')
    c    = 0
    code = 1
    for word in msg:
        if not _url_re.match(word):
            word = word.split('`')
            code -= 1
            w = 0
            for i in word:
                code = (code + 1) % 2
                if code:
                    word[w] = _escape_re.sub(r'\\\1', i)
                w += 1
            msg[c] = '`'.join(word)
        c += 1

    msg = ' '.join(msg)

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

# Get a channel
def _get_channel(client, name):
    if name not in channels:
        channels[name] = client.get_channel(_number_re.sub('', name))
    return channels[name]

# PRIVMSG
_number_re = re.compile('[^0-9]')
@_register_cmd('PRIVMSG')
def _on_privmsg(self, client, run, tags, cmd, args):
    if len(args) == 2:
        chan = _get_channel(client, args[0])
        if not chan: return
        msg  = args[-1][1:]
        if msg[:7].upper() == '\x01ACTION':
            msg = '\x1d' + msg[8:].replace('\x01', '') + '\x1d'
        msg = _irc_to_discord(msg)
        self.debug('Translated PRIVMSG:', msg)

        if hasattr(chan, 'send'):
            run(chan.send(msg))
        else:
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
    if len(args) != 2:
        return self.debug('Invalid call to NOTICE.')
    chan = _get_channel(client, args[0])
    if not chan: return
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

    if hasattr(chan, 'send'):
        run(chan.send(embed = embed))
    else:
        run(client.send_message(chan, embed = embed))

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

    if hasattr(discord, 'Activity'):
        game = discord.Activity(name = game,
            type = discord.ActivityType(ptype), url = url)
    else:
        game = discord.Game(name = game, type = ptype, url = url)
    self.debug('Changing online presence:', game)

    if tags.get('+discordapp.com/status'):
        try:
            status = discord.Status(tags['+discordapp.com/status'])
        except:
            print('WARNING: Invalid status sent to AWAY!')
            return
    else:
        status = discord.Status('online')

    if hasattr(discord, 'Activity'):
        run(client.change_presence(activity = game, status = status))
    else:
        run(client.change_presence(game = game, status = status))

# The discord class
class Discord(miniirc.IRC):
    _client = None
    msglen  = 2000

    def _run(self, coroutine):
        return asyncio.run_coroutine_threadsafe(coroutine, self._client.loop)

    def quote(self, *msg, force = None, tags = None):
        # Parse the message using miniirc's built-in parser to reduce redundancy
        msg = ' '.join(msg)
        self.debug('>>>', msg)
        cmd, hostmask, _, args = miniirc.ircv3_message_parser(msg)
        cmd = cmd.upper()
        del _

        if not isinstance(tags, dict):
            tags = {}

        if _outgoing_cmds.get(cmd):
            _outgoing_cmds[cmd](self, self._client, self._run, tags, cmd, args)
        else:
            self.debug('Unknown command run:', cmd)

    def _main(self):
        self.debug('Main loop running!')
        asyncio.set_event_loop(self._client.loop)

        try:
            self._client.loop.run_until_complete(self._client.start(self.ip))
        except:
            raise
            pass
        print('Finished')
        self.connected = False
        self.debug('Disconnected!')

        if self.persist:
            self.debug('Reconnecting in 5 seconds...')
            time.sleep(5)
            self._main_lock = None
            self.connect()

    def connect(self):
        if self.connected:
            self.debug('Already connected!')
            return
        self.connected = True
        self.debug('Connecting...')

        if self._client:
            asyncio.set_event_loop(self._client.loop)
        else:
            self._client = discord.Client()
        @self._client.event
        @asyncio.coroutine
        def on_message(message):
            yield from _handle_privmsg(self, message)

        self.main()

    def disconnect(self):
        raise NotImplementedError

    def get_server_count(self):
        if not self._client:
            return 0

        if hasattr(self._client, 'guilds'):
            return len(self._client.guilds)
        return len(self._client.servers)

# Add get_server_count equivalent to IRC.
miniirc.IRC.get_server_count = lambda irc : 1 if irc.connected else 0
