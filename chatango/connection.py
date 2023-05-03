import asyncio
import aiohttp
import sys
import traceback
from typing import Optional

from .exceptions import AlreadyConnectedError


class Connection:
    def __init__(self, client):
        self.client = client
        self._connected = False
        self._connection = None
        self._recv_task = None
        self._ping_task = None
        self._first_command = True

    async def connect(
        self,
        user_name: Optional[str] = None,
        password: Optional[str] = None,
    ):
        if self.connected:
            raise AlreadyConnectedError(getattr(self, "name", None), self)
        self._first_command = True
        await self._connect(u=user_name, p=password)
        self._recv_task = asyncio.create_task(self._do_recv())
        self._ping_task = asyncio.create_task(self._do_ping())

    @property
    def connected(self):
        return self._connected

    async def cancel(self):
        self._connected = False
        self._recv_task.cancel()
        self._ping_task.cancel()
        await self._connection.close()

    async def _send_command(self, *args, terminator="\r\n\0"):
        message = ":".join(args) + terminator
        if not self._connection._closed:
            await self._connection.send_str(message)

    async def _do_ping(self):
        while True:
            await asyncio.sleep(20)
            # ping is an empty message
            await self._send_command("\r\n", terminator="\x00")
            await self.client._call_event("ping", self)
            if not self.connected:
                break

    async def _do_recv(self):
        while True:
            try:
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
                    except asyncio.exceptions.CancelledError:
                        break
                    except:
                        if self.client.debug:
                            print("Error while handling command", cmd, file=sys.stderr)
                            traceback.print_exc(file=sys.stderr)
                elif self.client.debug:
                    print(
                        self, "Unhandled received command", cmd, args, file=sys.stderr
                    )
                if not self.connected:
                    break
            except aiohttp.WSServerDisconnectedError:
                print("Lost connection to server")
                await self.cancel()
                await asyncio.sleep(10)
                try:
                    await self.login()
                except Exception as e:
                    print(f"Failed to reconnect: {e}")


class Socket:  # resolver for socket client
    def __init__(self, client):
        self.client = client
        self._first = True
        self._connected = False
        self._recv = None
        self._connection = None
        self._recv_task = None
        self._ping_task = None

    async def connect(
        self,
        user_name: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """
        user_name, password. For the socket client
        """
        if self.connected:
            raise AlreadyConnectedError(getattr(self, "name", None), self)
        self._recv, self._connection = await asyncio.open_connection(
            f"{self.server}", self.port
        )
        self._recv_task = asyncio.create_task(self._do_recv())
        self._ping_task = asyncio.create_task(self._do_ping())
        await self._login(user_name, password)

    @property
    def connected(self):
        return self._connected

    async def cancel(self):
        self._connected = False
        self._recv_task.cancel()
        self._ping_task.cancel()
        await self._connection.close()

    async def _send_command(self, *args, terminator="\r\n\0"):
        if self._first_command:
            terminator = "\x00"
            self._first_command = False
        else:
            terminator = "\r\n\0"
        message = ":".join(args) + terminator
        self._connection.write(message.encode())
        await self._connection.drain()

    async def _do_ping(self):
        while True:
            await asyncio.sleep(20)
            # ping is an empty message
            await self._send_command("\r\n", terminator="\x00")
            await self.client._call_event("ping", self)
            if not self.connected:
                break

    async def _do_recv(self):
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
                self._recv.close()
                print(f"Disconnected from {self}")
            if not self.connected:
                break
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
                    print("Error while handling command", cmd, file=sys.stderr)
                    traceback.print_exc(file=sys.stderr)
        elif __debug__:
            print("Unhandled received command", cmd, file=sys.stderr)
