from .exceptions import AlreadyConnectedError, NotConnectedError

import typing
import asyncio
import aiohttp
import sys
import traceback
import socket

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
        self._connected = True
        await self._connect(u=user_name, p=password)
        self._recv_task = asyncio.create_task(self._do_recv())
        self._ping_task = asyncio.create_task(self._do_ping())

    @property
    def connected(self):
        return self._connected

    async def _send_command(self, *args, terminator="\r\n\0"):
        message = ":".join(args) + terminator
        if not self._connection._closed:
            await self._connection.send_str(message)

    async def _do_ping(self):
        await asyncio.sleep(20)
        # ping is an empty message
        await self._send_command("\r\n", terminator="\x00")
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


class Socket: #resolver for socket client
    def __init__(self, client):
        self.client = client
        self._connected = False
        self._recv = None
        self._buffer = None
        self._recv_task = None
        self._ping_task = None

    async def connect(self, user_name: typing.Optional[str] = None, password: typing.Optional[str] = None):
        """
        user_name, password. For the socket client
        """
        if self.connected:
            raise AlreadyConnectedError(getattr(self, "name", None), self)
        self._recv, self._buffer = await asyncio.open_connection(
            f"{self.server}", self.port)
        self._connected = True
        await self._login(user_name, password)
        self._recv_task = asyncio.create_task(self._do_recv())
        self._ping_task = asyncio.create_task(self._do_ping())

    @property
    def connected(self):
        return self._connected

    async def _send_command(self, *args, terminator="\r\n\0"): #changed cuz i can
        message = ":".join(args) + terminator
        self._buffer.write(message.encode())
        await self._buffer.drain()

    async def _do_ping(self):
        await asyncio.sleep(20)
        # ping is an empty message
        await self._send_command("\r\n", terminator="\x00")
        await self.client._call_event("ping", self)
        self._ping_task = asyncio.create_task(self._do_ping())

    async def _do_recv(self):
        while True:
            rcv = await self._recv.read(2048) #TODO if the rcv is higher than bytes, may is cutted
            await asyncio.sleep(0.0001)
            if rcv:  # si recibe datos.
                data = rcv.decode()
                if data == "\r\n\x00": #pong
                    await self._do_process("")
                else:
                    recv = data.split("\r\n\x00") #event
                    for _data in recv:
                        if _data != "":
                            await self._do_process(_data)
            else:
                self._recv.close()
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
            print("Unhandled received command", cmd, file=sys.stderr)
