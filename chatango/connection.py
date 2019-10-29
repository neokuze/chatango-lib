import typing
import asyncio
import aiohttp
import sys
import traceback

from .exceptions import AlreadyConnectedError, NotConnectedError


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

    async def _connect(self, user_name: typing.Optional[str], password: typing.Optional[str]):
        """Responsable of setting self._conneciton to a valid connection"""
        raise NotImplementedError

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
        try:
            await self._connection.send_str(message)
        except Exception as error:
            raise NotConnectedError
            
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
            args = args.split(":")
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
