import asyncio
import aiohttp
import inspect
import typing

from .pm import PM
from .room import Room
from .exceptions import AlreadyConnectedError, NotConnectedError

version = 0.280


class Client:
    def __init__(self, aiohttp_session: typing.Optional[aiohttp.ClientSession] = None):
        if aiohttp_session is None:
            aiohttp_session = aiohttp.ClientSession()

        self.aiohttp_session = aiohttp_session
        self.loop = self.aiohttp_session.loop
        self.pm = PM(self)

        self.debug = True
        self._rooms = {}
        self._running = False
        self._default_user_name = None
        self._default_password = None

    async def join(self, room_name: str) -> Room:
        room_name = room_name.lower()
        if room_name in self._rooms:
            raise AlreadyConnectedError(room_name, self._rooms[room_name])
        room = Room(self, room_name)
        await room.connect(self._default_user_name, self._default_password)
        return room

    async def leave(self, room_name: str):
        room_name = room_name.lower()
        if room_name not in self._rooms:
            raise NotConnectedError(room_name)
        # has to be in the dict until it's fully disconnected
        room = self._rooms[room_name]
        await room.disconnect()
        del self._rooms[room_name]

    async def start(self):
        self.styles = styles()
        self._running = True
        if self._default_user_name and self._default_password and self._default_pm:
            await self.pm.connect(self._default_user_name, self._default_password)
        await self._call_event("init")

    def default_user(self, user_name: str, password: typing.Optional[str] = None, pm=False):
        self._default_user_name = user_name
        self._default_password = password
        self._default_pm = pm

    async def stop(self):
        for room in self._rooms.values():
            await room.disconnect()
        self._rooms.clear()
        self._running = True

    async def enableBg(self, activo=True):
        """Enable background if available."""
        self.bgmode = activo
        for room in self._rooms:
            await self._rooms[room].setBgMode(int(activo))

    @property
    def running(self):
        return self._running

    async def on_event(self, event: str, *args: typing.Any, **kwargs: typing.Dict[str, typing.Any]):
        pass

    async def _call_event(self, event: str, *args, **kwargs):
        attr = f"on_{event}"
        await self.on_event(event, *args, **kwargs)
        if hasattr(self, attr):
            await getattr(self, attr)(*args, **kwargs)

    def event(self, func, name=None):
        assert inspect.iscoroutinefunction(func)
        if name is None:
            event_name = func.__name__
        else:
            event_name = name
        setattr(self, event_name, func)


class styles:
    def __init__(self):
        self._nameColor = str("00000")
        self._fontColor = str("00000")
        self._fontSize = 11
        self._fontFace = 1
        self._bg_on = True

    @property
    def bg_on(self):
        return int(self._bg_on)

    @property
    def default(self):
        size = str(self._fontSize)
        face = str(self._fontFace)
        return f"<f x{size}{self._fontColor}='{face}'>"
