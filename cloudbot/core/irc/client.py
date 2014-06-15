from _ssl import PROTOCOL_SSLv23
import asyncio
import logging
import ssl
from ssl import SSLContext

from cloudbot.core.permissions import PermissionManager
from cloudbot.core.irc.protocol import IRCProtocol
from cloudbot.core.events import BaseEvent

logger = logging.getLogger("cloudbot")


class Connection:
    """ A BotConnection represents each connection the bot makes to an IRC server
    :type bot: cloudbot.core.bot.CloudBot
    :type name: str
    :type channels: list[str]
    :type config: dict[str, unknown]
    :type ssl: bool
    :type server: str
    :type port: int
    :type logger: logging.Logger
    :type nick: str
    :type vars: dict
    :type history: dict[str, list[tuple]]
    :type permissions: PermissionManager
    :type connected: bool
    :type protocol: cloudbot.core.irc.protocol.IRCProtocol
    """

    def __init__(self, bot, name, server, nick, port=6667, use_ssl=False, channels=None, config=None,
                 readable_name=None):
        """
        :type bot: cloudbot.core.bot.CloudBot
        :type name: str
        :type server: str
        :type nick: str
        :type port: int
        :type use_ssl: bool
        :type logger: logging.Logger
        :type channels: list[str]
        :type config: dict[str, unknown]
        """
        self.bot = bot
        self.loop = bot.loop
        self.name = name
        if readable_name:
            self.readable_name = readable_name
        else:
            self.readable_name = name

        if channels is None:
            self.channels = []
        else:
            self.channels = channels

        if config is None:
            self.config = {}
        else:
            self.config = config

        self.ssl = use_ssl
        self.server = server
        self.port = port
        self.nick = nick
        self.vars = {}
        self.history = {}

        # create permissions manager
        self.permissions = PermissionManager(self)

        # transport and protocol
        self.transport = None
        self.protocol = None

        ignore_cert_errors = True

        if self.ssl:
            self.ssl_context = SSLContext(PROTOCOL_SSLv23)
            if ignore_cert_errors:
                self.ssl_context.verify_mode = ssl.CERT_NONE
            else:
                self.ssl_context.verify_mode = ssl.CERT_REQUIRED
        else:
            self.ssl_context = None

        self.timeout = 300

        self.connected = False
        # if we've quit
        self._quit = False

    @asyncio.coroutine
    def connect(self):
        """
        Connects to the IRC server. This by itself doesn't start receiving or sending data.
        """
        # connect to the irc server
        if self.connected:
            logger.info("[{}] Reconnecting".format(self.readable_name))
            self.transport.close()
        else:
            self.connected = True
            logger.info("[{}] Connecting".format(self.readable_name))

        self.transport, self.protocol = yield from self.loop.create_connection(
            lambda: IRCProtocol(self.loop, self.connect, self.readable_name), host=self.server,
            port=self.port, ssl=self.ssl_context,
        )

        # send the password, nick, and user
        self.set_pass(self.config["connection"].get("password"))
        self.set_nick(self.nick)
        self.cmd("USER", [self.config.get('user', 'cloudbot'), "3", "*",
                          self.config.get('realname', 'CloudBot - http://git.io/cloudbot')])

    @asyncio.coroutine
    def _advance(self):
        """Internal coroutine that just keeps the protocol message queue going.
        Called once after a connect and should never be called again after
        that.
        """
        # TODO this is currently just to keep the message queue going, but
        # eventually it should turn them into events and stuff them in an event
        # queue
        yield from self._read_message()

        asyncio.async(self._advance(), loop=self.loop)

    @asyncio.coroutine
    def _read_message(self):
        """Internal dispatcher for messages received from the protocol."""
        message = yield from self.protocol.message_queue.get()

        # this does nothing now
        handler = getattr(self, '_handle_' + message.command, None)
        if handler:
            handler(message)
        else:
            self._handle_generic(message)

    def _handle_generic(self, message):
        # TODO: Parse nick, user, host and mask somewhere in here
        event = BaseEvent(conn=self, irc_message=message)
        asyncio.async(self.bot.process(event))

    def quit(self, reason=None):
        if self._quit:
            return
        self._quit = True
        if reason:
            self.cmd("QUIT", [reason])
        else:
            self.cmd("QUIT")

    def close(self):
        if not self._quit:
            self.quit()
        if not self.connected:
            return
        self.transport.close()
        self.connected = False

    # various functions used to implement IRC commands
    def set_pass(self, password):
        """
        :type password: str
        """
        if password:
            self.cmd("PASS", [password])

    def set_nick(self, nick):
        """
        :type nick: str
        """
        self.cmd("NICK", [nick])

    def join(self, channel):
        """ makes the bot join a channel
        :type channel: str
        """
        self.cmd("JOIN", [channel])
        if channel not in self.channels:
            self.channels.append(channel)

    def part(self, channel):
        """ makes the bot leave a channel
        :type channel: str
        """
        self.cmd("PART", [channel])
        if channel in self.channels:
            self.channels.remove(channel)

    def msg(self, target, text):
        """ makes the bot send a PRIVMSG to a target
        :type text: str
        :type target: str
        """
        self.cmd("PRIVMSG", [target, text])

    def ctcp(self, target, ctcp_type, text):
        """ makes the bot send a PRIVMSG CTCP to a target
        :type ctcp_type: str
        :type text: str
        :type target: str
        """
        out = "\x01{} {}\x01".format(ctcp_type, text)
        self.cmd("PRIVMSG", [target, out])

    def cmd(self, command, params=None):
        """
        :type command: str
        :type params: list[str]
        """

        if not self.connected:
            raise ValueError("Connection must be connected to irc server to use cmd")
        if params is None:
            params = []
        self.loop.call_soon_threadsafe(asyncio.async, self.protocol.send_message(command, params))
