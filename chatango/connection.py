import typing
import asyncio
import aiohttp
import sys
import traceback
import re, html

from .exceptions import AlreadyConnectedError, NotConnectedError
from .utils import virtual, has_flag
from .message import Message, MESSAGE_FLAGS

class Connection:
    def __init__(self, client):
        self.client = client
        self._connected = False
        self._connection = None
        self._recv_task = None
        self._ping_task = None
        self._first_command = True

    async def connect(self, user_name: typing.Optional[str] = None, password: typing.Optional[str] = None):
        if self.connected:
            raise AlreadyConnectedError(getattr(self, "name", None), self)
        self._first_command = True
        await self._connect(user_name, password)
        self._connected = True
        self._recv_task = asyncio.create_task(self._do_recv())
        self._ping_task = asyncio.create_task(self._do_ping())
        await self.client._call_event("connect", self)

    async def disconnect(self):
        if not self.connected:
            raise NotConnectedError(getattr(self, "name", None), self)
        await self._disconnect()
        await self.client._call_event("disconnect", self)

    @property
    def connected(self):
        return self._connected

    @virtual
    async def _connect(self, user_name: typing.Optional[str], password: typing.Optional[str]):
        """Responsable of setting self._conneciton to a valid connection"""

    async def _disconnect(self):
        await self._connection.disconnect()
        self._connected = False
        self._recv_task.cancel()
        self._ping_task.cancel()
        try:
            await self._recv_task
        except asyncio.CancelledError:
            pass
        try:
            await self._ping_task
        except asyncio.CancelledError:
            pass
        self._recv_task = None
        self._connection = None
        self._ping_task = None

    async def _send_command(self, *args: str):
        if self._first_command:
            terminator = "\0"
            self._first_command = False
        else:
            terminator = "\r\n\0"
        message = ":".join(args) + terminator
        await self._connection.send_str(message)

    async def _do_ping(self):
        await asyncio.sleep(20)
        # ping is an empty message
        await self._send_command("")
        await self.client._call_event("ping", self)
        self._ping_task = asyncio.create_task(self._do_ping())

    async def _do_recv(self):
        while True:
            message = await self._connection.receive()
            assert message.type is aiohttp.WSMsgType.TEXT
            if not message.data:
                # pong
                cmd = "pong"
                args = ""
            else:
                cmd, _, args = message.data.partition(":")
            if hasattr(self, f"_rcmd_{cmd}"):
                try:
                    await getattr(self, f"_rcmd_{cmd}")(args)
                except:
                    if __debug__:
                        print("Error while handling command",
                            cmd, file=sys.stderr)
                        traceback.print_exc(file=sys.stderr)
            elif __debug__:
                print("Unhandled received command", cmd, file=sys.stderr)
        raise ConnectionAbortedError

    async def _rcmd_ok(room, args):
        args = args.split(":")
        room.owner = args[0]
        room._unid = args[1]
        room._user = args[3]

    async def _rcmd_inited(room, args):
        pass
    async def _rcmd_pong(room, args):
        await room.client._call_event("pong")
    async def _rcmd_n(room, user_count):
        room.user_count = int(user_count, 16)
    async def _rcmd_i(room, args):
        await room._rcmd_b(args)
    async def _rcmd_b(room, args):
        args = args.split(":")
        _time = float(args[0])
        name, tname, puid, unid, msgid, ip, flags = args[1:8]
        body = args[9]
        msg = Message()
        msg._room = room
        msg._time = float(_time)
        msg._user = name
        msg._puid = int(puid)
        msg._tempname = tname
        msg._msgid = str(msgid)
        msg._unid = str(unid)
        msg._ip = str(ip)
        msg._body = html.unescape(
            re.sub("<(.*?)>", "", body.replace("<br/>", "\n"))
            )
        for key, value in MESSAGE_FLAGS.items():
            if has_flag(flags, value):
                msg._flags[key] = True
            else:
                msg._flags[key] = False
        room._mqueue[msg._msgid] = msg
    async def _rcmd_u(room, arg):
        args = arg.split(":")
        if args[0] in room._mqueue:
            msg = room._mqueue.pop(args[0])
            if msg._user != room._user:
                pass
            msg.attach(room, args[1])
            await room.client._call_event("message", msg)