import typing
import asyncio
import aiohttp
import sys
import traceback
import socket
from .exceptions import AlreadyConnectedError, NotConnectedError, WebsocketClosure

class Connection:
    def __init__(self, client, ws=True):
        self.client = client
        self._connected = False
        self.type = 'ws' if ws else 'sock'
        self._connection = None
        self._recv_task = None
        self._ping_task = None
        self._first_command = True
        self._recv = None if not ws else False

    @property
    def connected(self):
        return self._connected

    async def connect(self, user_name: typing.Optional[str] = None, password: typing.Optional[str] = None):
        if self.type == 'sock':
            return
        if self.connected:
            raise AlreadyConnectedError(getattr(self, "name", None), self)
        self._first_command = True
        await self._login(u=user_name, p=password)
        self._recv_task = asyncio.create_task(self.ws_do_recv())
        self._ping_task = asyncio.create_task(self._do_ping())

    async def sock_connect(self, user_name: typing.Optional[str] = None, password: typing.Optional[str] = None):
        """
        user_name, password. For the socket client
        """
        if self.type == 'ws':
            return
        if self.connected:
            raise AlreadyConnectedError(getattr(self, "name", None), self)
        self._recv, self._connection = await asyncio.open_connection(
            f"{self.server}", self.port)
        self._recv_task = asyncio.create_task(self.s_do_recv())
        self._ping_task = asyncio.create_task(self._do_ping())
        await self._login(user_name, password)

    async def _send_command(self, *args, terminator="\r\n\0"):
        message = ":".join(args) + terminator
        if self._first_command:
            terminator = "\x00"
            self._first_command = False
        else:
            terminator = "\r\n\0"
        if self.type == 'sock':
            self._connection.write(message.encode())
            await self._connection.drain()
        else:
            if not self._connection._closed:
                await self._connection.send_str(message)

    async def cancel(self):
        self._connected = False
        self._recv_task.cancel()
        self._ping_task.cancel()
        await self._connection.close()

    async def _do_ping(self):
        await asyncio.sleep(20)
        # ping is an empty message
        await self._send_command("\r\n", terminator="\x00")
        await self.client._call_event("ping", self)
        self._ping_task = asyncio.create_task(self._do_ping())

    async def ws_do_recv(self):
        while True:
            try:
                message = await self._connection.receive()
                if message.type is aiohttp.WSMsgType.TEXT:
                    await self._do_process(message.data)
                elif message.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING, aiohttp.WSMsgType.CLOSE):
                    raise WebsocketClosure
            except (asyncio.TimeoutError, WebsocketClosure) as error:
                if self.client.debug:
                    print(f"[{self.name} :Connection Rejected. ]", error)
                if self._connection.closed:
                    await self.cancel()
                    break
                
    async def s_do_recv(self):
        while True:
            # TODO if the rcv is higher than bytes, may is cutted
            rcv = await self._recv.read(2048)
            await asyncio.sleep(0.0001)
            if rcv:  # si recibe datos.
                data = rcv.decode()
                if data == "\r\n\x00":  # pong
                    await self._do_process("")
                else:
                    recv = data.split("\r\n\x00")  # event
                    for r in recv:
                        if r != "":
                            await self._do_process(r)
            else:
                await self.cancel()
                print(f"Disconnected from {self}")
        raise ConnectionAbortedError

    async def _do_process(self, recv):
        """
        Process socket event
        """
        if not recv:
            cmd = "pong"
            args = ""
        else:
            cmd, _, args = recv.partition(":")
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
            print("Unhandled received command",
                  cmd, repr(args), file=sys.stderr)
