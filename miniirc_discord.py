#!/usr/bin/python3
#
# miniirc_discord: Allows miniirc bots/clients to connect to Discord.
#
# Licensed under the MIT License:
# https://gitlab.com/luk3yx/miniirc_discord/LICENSE.md
#

import asyncio, discord, itertools, miniirc, re, threading, time, traceback

ver      = (0,6,0)
version  = '0.6.0'
__all__  = ['Discord', 'miniirc']

assert miniirc.ver >= (1, 8, 0), 'Please update miniirc!'
assert discord.version_info >= (2, 0, 0), 'Please update discord.py!'

def _hostmask(author):
    return (
        author.mention,
        f'{author.name}#{author.discriminator}',
        f'discord/{"bot" if author.bot else "user"}/<@{author.id}>'
    )


_MINIIRC_V2 = miniirc.ver >= (2, 0, 0)
_v1_only_colon = '' if _MINIIRC_V2 else ':'


async def _handle_privmsg(irc, message):
    if (irc._client.user == message.author and
            'echo-message' not in irc.active_caps):
        return

    # Create miniirc-style objects
    irc.debug('New message:', message)
    hostmask = _hostmask(message.author)

    # Create the tags
    msgid = str(message.id)
    tags = {
        'account': str(message.author.id),
        'draft/msgid': msgid,
        'msgid': msgid,
        'time':  message.created_at.strftime('%Y-%m-%dT%H:%M:%SZ'),
    }

    # Add a bot tag
    if message.author.bot:
        tags['bot'] = ''

    # Convert replies
    if message.type == discord.MessageType.reply and message.reference:
        tags['+draft/reply'] = str(message.reference.message_id)

    # Create the args
    channel = str(message.channel.id)

    if not isinstance(message.channel, discord.abc.PrivateChannel):
        channel = '#' + channel
    args = [channel, _v1_only_colon + message.content]

    irc.debug('Handling message:', hostmask, tags, args)
    irc._handle('PRIVMSG', hostmask, tags, args)


async def _handle_reaction(irc, payload):
    # DM reactions aren't currently supported since the user name isn't sent
    if payload.member is None or payload.emoji.name is None:
        return

    if (irc._client.user.id == payload.user_id and
            'echo-message' not in irc.active_caps):
        return

    irc._handle('TAGMSG', _hostmask(payload.member), {
        'account': str(payload.user_id),
        '+draft/reply': str(payload.message_id),
        '+draft/react': payload.emoji.name,
    }, [f'#{payload.channel_id}'])


_formatting_re = re.compile(
    r'\x02|\x1d|\x1f|\x1e|\x11|\x16|\x0f'
    r'|\x03([0-9]{1,2})?(?:,([0-9]{1,2}))?'
    r'|\x04([0-9a-fA-F]{6})?(?:,([0-9a-fA-F]{6}))?'
)
_md_chars = {'\x02': '**', '\x1d': '_', '\x1f': '__', '\x1e': '~~',
             '\x11': '`'}


class _TagManager:
    __slots__ = ('text', 'tags', 'open_tags')

    def __init__(self) -> None:
        self.text = []
        self.tags = {}
        self.open_tags = {}

    def write_tags(self) -> None:
        if self.tags != self.open_tags:
            open_tags = tuple(self.open_tags)
            tags = tuple(self.tags)
            i = 0
            for a, b in zip(open_tags, tags):
                if a != b:
                    break
                i += 1

            self.text.append('\u200b'.join(itertools.chain(
                reversed(open_tags[i:]), tags[i:]
            )))
            self.open_tags = self.tags.copy()

    def write(self, s):
        if s:
            self.write_tags()
            self.text.append(s)

    def toggle(self, tag):
        if tag in self.tags:
            del self.tags[tag]
        else:
            self.tags[tag] = True
            # Fix ordering
            if self.tags == self.open_tags:
                self.tags = self.open_tags.copy()


def _irc_to_discord(msg):
    """ Converts IRC formatting codes to Discord markdown. """
    msg = discord.utils.escape_markdown(msg).replace('\\`', '`')

    tags = _TagManager()
    prev_end = start = 0
    for match in _formatting_re.finditer(msg):
        start = match.start()
        tags.write(msg[prev_end:start])
        char = msg[start]
        if char in _md_chars:
            tags.toggle(_md_chars[char])
        elif char == '\x0f':
            tags.tags.clear()
        elif char == '\x03':
            # Handle spoilers
            fg = match.group(1)
            bg = match.group(2)
            if (fg and bg and int(fg) == int(bg)) or '||' in tags.tags:
                tags.toggle('||')
        prev_end = match.end()

    tags.write(msg[prev_end:])
    tags.tags.clear()
    tags.write_tags()
    return ''.join(tags.text)

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
    try:
        channel_id = int(name.strip('#<@!> '))
    except ValueError:
        return
    return client.get_partial_messageable(channel_id)

async def _send_msg(channel, tags, content=None, *, embed=None):
    if '+draft/reply' in tags:
        message_id = int(tags['+draft/reply'])

        # Add reactions
        # The variant selector (U+FE0F) is removed, GNOME's emoji picker adds
        # this but it isn't accepted by Discord's API on most emoji.
        if '+draft/react' in tags:
            orig_msg = channel.get_partial_message(message_id)
            await orig_msg.add_reaction(tags['+draft/react'].rstrip('\ufe0f'))

        # Don't attempt to reply to empty TAGMSGs
        if content is None and embed is None:
            return

        # Get a reference with fail_if_not_exists=False
        reference = discord.MessageReference(
            message_id=message_id,
            channel_id=channel.id,
            fail_if_not_exists=False,
        )

        try:
            await channel.send(content, embed=embed, reference=reference)
        except discord.Forbidden:
            # If the bot doesn't have "view message history" permissions then
            # fall back to normal message sending. This isn't perfect because
            # there will be an extra request but it's better than not sending
            # anything.
            pass
        else:
            return
    elif content is None and embed is None:
        # Don't send nothing
        return

    await channel.send(content, embed=embed)

# PRIVMSG
@_register_cmd('PRIVMSG')
async def _on_privmsg(self, client, tags, cmd, args):
    if len(args) == 2:
        chan = _get_channel(client, args[0])
        if not chan: return
        msg = args[-1]
        if msg[:7].upper() == '\x01ACTION':
            msg = '\x1d' + msg[8:].replace('\x01', '')
        msg = _irc_to_discord(msg)
        self.debug('Translated PRIVMSG:', msg)

        await _send_msg(chan, tags, msg)
    else:
        self.debug('Invalid call to PRIVMSG.')

# TAGMSG
@_register_cmd('TAGMSG')
async def _on_privmsg(self, client, tags, cmd, args):
    if len(args) > 0:
        chan = _get_channel(client, args[0])
        if chan:
            await _send_msg(chan, tags)

# IRC colour hex values
_colours = [
    0xffffff,  # White
    0x000000,  # Black
    discord.Colour.blue(),
    discord.Colour.green(),
    discord.Colour.red(),
    0xd2691e,  # Brown
    discord.Colour.magenta(),
    discord.Colour.orange(),
    discord.Colour.yellow(),
    discord.Colour.brand_green(),
    0x00ffff,  # Cyan
    0xe0ffff,  # Light cyan
    0xadd8e6,  # Light blue
    0xffc0cb,  # Pink
    discord.Colour.dark_grey(),  # Grey
    discord.Colour.light_grey(),  # Light grey

    # Colours 16-98
    0x470000, 0x472100, 0x474700, 0x324700, 0x004700, 0x00472c, 0x004747,
    0x002747, 0x000047, 0x2e0047, 0x470047, 0x47002a, 0x740000, 0x743a00,
    0x747400, 0x517400, 0x007400, 0x007449, 0x007474, 0x004074, 0x000074,
    0x4b0074, 0x740074, 0x740045, 0xb50000, 0xb56300, 0xb5b500, 0x7db500,
    0x00b500, 0x00b571, 0x00b5b5, 0x0063b5, 0x0000b5, 0x7500b5, 0xb500b5,
    0xb5006b, 0xff0000, 0xff8c00, 0xffff00, 0xb2ff00, 0x00ff00, 0x00ffa0,
    0x00ffff, 0x008cff, 0x0000ff, 0xa500ff, 0xff00ff, 0xff0098, 0xff5959,
    0xffb459, 0xffff71, 0xcfff60, 0x6fff6f, 0x65ffc9, 0x6dffff, 0x59b4ff,
    0x5959ff, 0xc459ff, 0xff66ff, 0xff59bc, 0xff9c9c, 0xffd39c, 0xffff9c,
    0xe2ff9c, 0x9cff9c, 0x9cffdb, 0x9cffff, 0x9cd3ff, 0x9c9cff, 0xdc9cff,
    0xff9cff, 0xff94d3, 0x000000, 0x131313, 0x282828, 0x363636, 0x4d4d4d,
    0x656565, 0x818181, 0x9f9f9f, 0xbcbcbc, 0xe2e2e2, 0xffffff
]
_embed_title_re = re.compile(
    r'^\x02([^\n]+)'
    r'(?:\x02(?:\x03(?:99(?:,99)?)?)?|\x0f)'
    r'\n(.*)$',
    re.DOTALL
)
_embed_colour_re = re.compile(
    r'^(?:\x03([0-9]{1,2})?(?:,([0-9]{1,2}))?)?(.*)$',
    re.DOTALL
)

# NOTICE
@_register_cmd('NOTICE')
async def _on_notice(self, client, tags, cmd, args):
    if len(args) != 2:
        return self.debug('Invalid call to NOTICE.')
    chan = _get_channel(client, args[0])
    if not chan: return

    match = _embed_colour_re.match(args[1])
    colour = _colours[int(match.group(1))] if match.group(1) else None

    msg = match.group(3)
    if '+discordapp.com/embed-title' in tags:
        # Legacy embed titles
        # This is retained for backwards compatibility but shouldn't be used as
        # it doesn't work with miniirc and miniirc_matrix.
        title = tags['+discordapp.com/embed-title']
    else:
        match = _embed_title_re.match(msg)
        if match:
            # "New" title detection (without any non-standard tags)
            # Usage: '\x02Embed title\x02\nEmbed content'
            title = match.group(1)
            msg = match.group(2)
        else:
            # No title
            title = ''

    embed = discord.Embed(title=_irc_to_discord(title) or None,
                          description=_irc_to_discord(msg), colour=colour)
    await _send_msg(chan, tags, embed=embed)

# AWAY
@_register_cmd('AWAY')
async def _on_away(self, client, tags, cmd, args):
    game = ' '.join(args)
    ptype = (tags and tags.get('+discordapp.com/type') or '').lower()
    url   = None
    if ptype == 'watching':
        ptype = 3
    elif ptype == 'listening to':
        ptype = 2
    elif ptype == 'streaming':
        ptype = 1
        url = 'https://www.twitch.tv/directory'
    else:
        ptype = 0

    game = discord.Activity(name=game, type=discord.ActivityType(ptype),
        url=url)
    self.debug('Changing online presence:', game)

    if tags.get('+discordapp.com/status'):
        try:
            status = discord.Status(tags['+discordapp.com/status'])
        except:
            print('WARNING: Invalid status sent to AWAY!')
            return
    else:
        status = discord.Status('online')

    await client.change_presence(activity=game, status=status)

# The discord class
class Discord(miniirc.IRC):
    _client = None
    __sendq = None
    msglen  = 2000

    def __init__(self, token=None, port=-1, nick='', channels=None, *,
            ping_interval=60, ns_identity=None, stateless_mode=True,
            **kwargs):
        if token is None:
            try:
                token = kwargs.pop('ip')
            except KeyError:
                raise TypeError("Discord.__init__() missing 1 required "
                    "positional argument: 'token'") from None

        self.stateless_mode = stateless_mode
        super().__init__(token, port, nick, ping_interval=0, **kwargs)

    @property
    def discord_client(self):
        if self.stateless_mode:
            return None
        return self._client

    @property
    def current_nick(self):
        if self._client is None or self._client.user is None:
            return self.nick
        return self._client.user.mention

    def _run(self, coroutine):
        self._loop.call_soon_threadsafe(self._loop.create_task, coroutine)

    def quote(self, *msg, force=None, tags=None) -> None:
        cmd, _, tags2, args = miniirc.ircv3_message_parser(' '.join(msg))
        if not _MINIIRC_V2 and args and args[-1].startswith(':'):
            args[-1] = args[-1][1:]
        self.send(cmd, *args, force=force, tags=tags or tags2)

    def send(self, cmd, *args, force=None, tags=None) -> None:
        cmd = cmd.upper()

        if not self.connected and not force:
            if self.debug_file:
                self.debug('>Q>', cmd, *args)
            if self.__sendq is None:
                self.__sendq = []
            self.__sendq.append((tags, args))
            return

        if self.debug_file:
            self.debug('>>>', cmd, *args)

        func = _outgoing_cmds.get(cmd)
        if func:
            if tags is None:
                tags = {}
            self._run(func(self, self._client, tags, cmd, args))
        else:
            self.debug('Unknown command run:', cmd)

    def _main(self):
        async def async_main():
            self.debug('Main loop running!')
            self._loop = asyncio.get_running_loop()
            async with self._client:
                await self._client.start(self.ip)

        try:
            asyncio.run(async_main())
        except Exception:
            traceback.print_exc()
        finally:
            self.connected = None
            del self._client
            self.debug('Disconnected!')

            if self.persist:
                self.debug('Reconnecting in 5 seconds...')
                time.sleep(5)
                self._main_lock = None
                self.connect()

    def connect(self):
        if self.connected is not None:
            self.debug('Already connected!')
            return
        self.connected = False
        self.debug('Connecting...')

        options = {}
        if self.stateless_mode:
            self._client = discord.Client(
                max_messages=None,
                fetch_offline_members=False,
                guild_subscriptions=False,
                intents=discord.Intents(
                    messages=True,
                    message_content=True,
                    reactions=True,
                ),
            )
        else:
            intents = discord.Intents.default()
            intents.message_content = True
            self._client = discord.Client(max_messages=None, intents=intents)

        @self._client.event
        async def on_message(message):
            await _handle_privmsg(self, message)

        @self._client.event
        async def on_raw_reaction_add(payload):
            await _handle_reaction(self, payload)

        @self._client.event
        async def on_ready():
            self.nick = self._client.user.mention
            self.active_caps = {'account-tag', 'message-tags', 'server-time'}
            if 'echo-message' in self.ircv3_caps:
                self.active_caps.add('echo-message')
            self._handle('001', ('001', '001', '001'), {}, [self.current_nick,
                f'{_v1_only_colon}Welcome to Discord {self.current_nick}'])

            sendq, self.__sendq = self.__sendq, None
            if sendq:
                for tags, args in sendq:
                    irc.send(*args, tags=tags)

        self._start_main_loop()

    def disconnect(self):
        if self.connected is not None:
            self._loop.close()

    def get_server_count(self):
        if not self._client:
            return 0

        return len(self._client.guilds)


# Add a get_server_count equivalent to IRC.
miniirc.IRC.get_server_count = lambda irc : 1 if irc.connected else 0
