import asyncio
import aiohttp
import sys
import traceback
import logging
from typing import Optional

from .exceptions import AlreadyConnectedError

logger = logging.getLogger(__name__)

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
            raise AlreadyConnectedError(getattr(self, "name", None))
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
                        logger.error(f"Error while handling command {cmd}")
                        traceback.print_exc(file=sys.stderr)
                else:
                    logger.error(f"{self} Unhandled received command {cmd} {args}")

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


