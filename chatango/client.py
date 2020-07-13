import asyncio
import aiohttp
import inspect
import typing, time

from .pm import PM
from .room import Room
from .exceptions import AlreadyConnectedError, NotConnectedError
from .utils import Task
from .message import Fonts

class Client:
    def __init__(self, aiohttp_session: typing.Optional[aiohttp.ClientSession] = None):
        if aiohttp_session is None:
            aiohttp_session = aiohttp.ClientSession()

        self.aiohttp_session = aiohttp_session
        self.loop = self.aiohttp_session.loop
        self.pm = PM(self)

        self.silent = int(2)
        self.debug = 1

        self._running = False
        self._rooms = {}
        self.errors = []
        self.__rcopy = {}
        self.__reconnect = []
        self._using_accounts = None
        self._default_user_name = None
        self._default_password = None
        
    def __dir__(self):
        return [x for x in
                set(list(self.__dict__.keys()) + list(dir(type(self)))) if
                x[0] != '_']
    @property
    def accounts(self):
        if self._using_accounts:
            return [(x, self._using_accounts[x][0]) for x in range(
                len(self._using_accounts))]
        return None

    async def join(self, room_name: str) -> Room:
        room_name = room_name.lower()
        if room_name in self._rooms:
            roomname, isconnected, canreconnect = AlreadyConnectedError(room_name, self._rooms[room_name]).check()
            if not isconnected and canreconnect:
                await self.leave(roomname)
                self.check_rooms(roomname)
        room = Room(self, room_name)
        await room.connect(self._default_user_name, self._default_password)
        return room

    async def leave(self, room_name: str, reconnect=None):
        room_name = room_name.lower()
        if room_name not in self._rooms:
            return f"{False if NotConnectedError(room_name) else True}"
        # has to be in the dict until it's fully disconnected
        if room_name in self._rooms and self._rooms[room_name]._connection is not None:
            if reconnect == None:
                reconnect = self.get_room(room_name).reconnect
            else:
                reconnect = self.get_room(room_name)._reconnect = reconnect
            await self._rooms[room_name]._connection.close()      
            self._rooms[room_name]._recv_task.cancel()
            self._rooms[room_name]._ping_task.cancel()
            if room_name in self._rooms:
                del self._rooms[room_name]
            if not reconnect: await self._call_event("disconnect", room_name)
            if reconnect == True:
                await self._call_event("reconnect", room_name)
                await self.join(room_name)
        return True

    async def start(self):
        self._running = True
        await self._call_event("init")
        if self._default_user_name and self._default_password and self._default_pm == True:
            await self.pm.connect(self._default_user_name, self._default_password)
        await self._call_event("start")
        asyncio.create_task(self._dead_rooms)

    @property
    def rooms(self):
        return [self._rooms[x] for x in self._rooms]

    def get_room(self, room_name: str):
        if room_name in [room.name for room in self.rooms]:
            for room in self.rooms:
                if room.name == room_name:
                    return room
        return False

    def check_rooms(self, room):
        for key in self._rooms:
            if key != room:
                self.__rcopy[key] = self._rooms[key]
        self._rooms.clear()
        self._rooms.update(self.__rcopy)
        self.__rcopy.clear()
        return True

    def default_user(self, user_name: str, password: typing.Optional[str] = None, pm=True, accounts=None):
        self._using_accounts = accounts # [[user, pass]]
        self._default_user_name = user_name
        self._default_password = password
        self._default_pm = pm

    async def stop(self):
        if self.pm._connected == True:
            self.pm._connection.close()
            self.pm._ping_task.cancel()
            self.pm._recv_task.cancel()
            print(f"Disconnected from {self.pm}")
        for room in self.rooms:
            await self.leave(room.name, reconnect=False)
        self._running = False

    async def enable_bg(self, active=True):
        """Enable background if available."""
        self.bgmode = active
        for room in self._rooms:
            await self._rooms[room].set_bg_mode(int(active))

    @property
    def running(self):
        return self._running

    async def on_event(self, event: str, *args: typing.Any, **kwargs: typing.Dict[str, typing.Any]):
        if int(self.debug) == 3:
            print(event, repr(args), repr(kwargs))

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
            
    def set_interval(self, tiempo, funcion, *args, **kwargs):
        """
        Llama a una función cada intervalo con los argumentos indicados
        @param funcion: La función que será invocada
        @type tiempo int
        @param tiempo:intervalo
        """
        task = Task(tiempo, funcion, True, *args, **kwargs)
        
        return task

    def set_timeout(self, tiempo, funcion, *args, **kwargs):
        """
        Llama a una función cada intervalo con los argumentos indicados
        @param tiempo: Tiempo en segundos hasta que se ejecute la función
        @param funcion: La función que será invocada
        """
        task = Task(tiempo, funcion, False, *args, **kwargs)
        
        return task

    async def _dead_rooms(self): # Reconnect 
        while True: 
            _ = [await self.leave(room) for room in self._rooms 
              if self._rooms[room].connection == None or self._rooms[room].connection.closed]
            await asyncio.sleep(2)
