#!/usr/bin/python3
#
# miniirc_discord: Allows miniirc bots/clients to connect to Discord.
#
# Licensed under the MIT License:
# https://gitlab.com/luk3yx/miniirc_discord/LICENSE.md
#

import asyncio, discord, miniirc, re, time, traceback

ver      = (0,5,12)
version  = '0.5.12'
__all__  = ['Discord', 'miniirc']
channels = {}

assert hasattr(discord, 'abc'), 'Please update discord.py!'

def _hostmask(author):
    return (
        author.mention,
        '{}#{}'.format(author.name, author.discriminator),
        'discord/{}/<@{}>'.format('bot' if author.bot else 'user', author.id)
    )

async def _handle_privmsg(irc, message):
    if irc._client.user == message.author:
        return

    # Create miniirc-style objects
    irc.debug('New message:', message)
    hostmask = _hostmask(message.author)

    # Create the tags
    tags = {
        'draft/msgid':  str(message.id),
        'server-time':  message.created_at.strftime('%Y-%m-%dT%H:%M:%SZ'),
    }

    # Create the args
    channel = str(message.channel.id)

    if not isinstance(message.channel, discord.abc.PrivateChannel):
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
_number_re = re.compile('[^0-9]')
def _get_channel(client, name):
    if name not in channels:
        channels[name] = client.get_channel(int(_number_re.sub('', name)))
    return channels[name]

# PRIVMSG
@_register_cmd('PRIVMSG')
async def _on_privmsg(self, client, tags, cmd, args):
    if len(args) == 2:
        chan = _get_channel(client, args[0])
        if not chan: return
        msg = args[-1]
        if msg.startswith(':'):
            msg = msg[1:]
        if msg[:7].upper() == '\x01ACTION':
            msg = '\x1d' + msg[8:].replace('\x01', '') + '\x1d'
        msg = _irc_to_discord(msg)
        self.debug('Translated PRIVMSG:', msg)

        await chan.send(msg)
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
async def _on_notice(self, client, tags, cmd, args):
    if len(args) != 2:
        return self.debug('Invalid call to NOTICE.')
    chan = _get_channel(client, args[0])
    if not chan: return
    title = tags.get('+discordapp.com/embed-title') or ''
    msg = args[-1]
    if msg.startswith(':'):
        msg = msg[1:]
    colour = None
    if msg.startswith('\x03') and len(msg) > 2:
        try:
            colour = _colours[int(msg[1])]
        except:
            pass
    title, msg = _irc_to_discord(title), _irc_to_discord(msg)
    embed = discord.Embed(title = title or None, description = msg,
        colour = colour or discord.Embed.Empty)

    await chan.send(embed = embed)

# AWAY
@_register_cmd('AWAY')
async def _on_away(self, client, tags, cmd, args):
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

    game = discord.Activity(name = game, type = discord.ActivityType(ptype),
        url = url)
    self.debug('Changing online presence:', game)

    if tags.get('+discordapp.com/status'):
        try:
            status = discord.Status(tags['+discordapp.com/status'])
        except:
            print('WARNING: Invalid status sent to AWAY!')
            return
    else:
        status = discord.Status('online')

    await client.change_presence(activity = game, status = status)

# The discord class
class Discord(miniirc.IRC):
    _client = None
    _sendq  = None
    msglen  = 2000

    def _run(self, coroutine):
        return asyncio.run_coroutine_threadsafe(coroutine, self._client.loop)

    def quote(self, *msg, force=None, tags=None):
        # Parse the message using miniirc's built-in parser to reduce redundancy
        msg = ' '.join(msg)
        self.debug('>>>', msg)
        cmd, hostmask, _, args = miniirc.ircv3_message_parser(msg)
        cmd = cmd.upper()
        del _

        if not isinstance(tags, dict):
            tags = {}

        if not self.connected:
            self._sendq.append((tags, *msg))

        if _outgoing_cmds.get(cmd):
            self._run(_outgoing_cmds[cmd](self, self._client, tags, cmd, args))
        else:
            self.debug('Unknown command run:', cmd)

    def _main(self):
        self.debug('Main loop running!')
        asyncio.set_event_loop(self._client.loop)

        try:
            self._client.loop.run_until_complete(self._client.start(self.ip))
        except:
            traceback.print_exc()

        self.connected = None
        del self._client
        self.debug('Disconnected!')

        if self.persist:
            self.debug('Reconnecting in 5 seconds...')
            time.sleep(5)
            self._main_lock = None
            self.connect()

    def connect(self):
        if self.connected != None:
            self.debug('Already connected!')
            return
        self.connected = False
        self.debug('Connecting...')

        loop = asyncio.new_event_loop()
        self._client = discord.Client(loop=loop, max_messages=0)

        @self._client.event
        async def on_message(message):
            await _handle_privmsg(self, message)

        @self._client.event
        async def on_ready():
            self.nick = self._client.user.mention
            self._handle('001', ('', '', ''), {}, [self.nick,
                ':Welcome to Discord ' + self.nick])

        self.main()

    def disconnect(self):
        raise NotImplementedError

    def get_server_count(self):
        if not self._client:
            return 0

        return len(self._client.guilds)

    def __init__(self, token=None, port=-1, nick='', channels=None, *,
            ping_interval=60, ns_identity=None, **kwargs):
        if token is None:
            try:
                token = kwargs.pop('ip')
            except KeyError:
                raise TypeError("Discord.__init__() missing 1 required "
                    "positional argument: 'token'") from None

        super().__init__(token, port, nick, ping_interval=0, **kwargs)

# Add get_server_count equivalent to IRC.
miniirc.IRC.get_server_count = lambda irc : 1 if irc.connected else 0

# Compatibility
if hasattr(miniirc.IRC, 'sendq'):
    p = property(lambda self : self.sendq)
    @p.setter
    def p(self, value):
        self.sendq = value
    Discord._sendq = p

    del p
