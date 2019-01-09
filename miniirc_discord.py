#!/usr/bin/python3
#
# miniirc_discord: Allows miniirc bots/clients to connect to Discord.
# Attempts to use IRCv3 tags to allow reactions etc to be sent.
#
# Licensed under the MIT License:
# https://gitlab.com/luk3yx/miniirc_discord/LICENSE.md
#

import asyncio, discord, miniirc, re, time

ver      = (0,3,12)
version  = '0.3.12'
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

class Discord(miniirc.IRC):
    _client = None

    def _run(self, coroutine):
        return asyncio.run_coroutine_threadsafe(coroutine, self._client.loop)

    def quote(self, *msg, force = None):
        # Parse the message using miniirc's built-in parser to reduce redundancy
        msg = ' '.join(msg)
        self.debug('>>>', msg)
        cmd, hostmask, tags, args = miniirc.ircv3_message_parser(msg)
        cmd = cmd.upper()

        if cmd in ('PRIVMSG', 'NOTICE'):
            if len(args) == 2 and args[0] in channels:
                chan = channels[args[0]]
                msg  = args[-1][1:]
                if msg[:7].upper() == '\x01ACTION':
                    msg = '\x1d' + msg[8:].replace('\x01', '') + '\x1d'
                msg = _irc_to_discord(msg)
                self.debug('Translated PRIVMSG:', msg)
                self._run(self._client.send_message(chan, msg))
            else:
                self.debug('Invalid call to PRIVMSG.')
        elif cmd == 'AWAY':
            game = ' '.join(args)
            if game.startswith(':'):
                game = game[1:]
            self.debug('Changing online presence:', game)
            game = discord.Game(name = game)
            self._run(self._client.change_presence(game = game))

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
