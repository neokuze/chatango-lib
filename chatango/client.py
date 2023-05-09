import asyncio
import re
import logging
from typing import Coroutine, Dict, List, Optional

from .pm import PM
from .room import Room
from .exceptions import NotConnectedError
from .handler import EventHandler

logger = logging.getLogger(__name__)


class Client(EventHandler):
    def __init__(
        self, username: str = "", password: str = "", rooms: List[str] = [], pm=False
    ):
        self._tasks: List[asyncio.Task] = []
        self.rooms: Dict[str, Room] = {}
        self.pm: Optional[PM] = None
        self.use_pm = pm
        self.initial_rooms: List[str] = rooms
        self.username = username
        self.password = password

    def add_task(self, coro: Coroutine):
        self._tasks.append(asyncio.create_task(coro))

    def _prune_tasks(self):
        self._tasks = [task for task in self._tasks if not task.done()]

    async def _task_loop(self, forever=False):
        while self._tasks or forever:
            await asyncio.gather(*self._tasks)
            self._prune_tasks()
            if forever:
                await asyncio.sleep(0.1)

    async def run(self, *, forever=False):
        await self._call_event("init")

        if not self.use_pm and not self.initial_rooms:
            logger.error("No rooms or PM to join. Exiting.")
            return

        if self.use_pm:
            self.join_pm()

        for room_name in self.initial_rooms:
            self.join_room(room_name)

        await self._call_event("start")
        await self._task_loop(forever)

    def join_pm(self):
        if not self.username or not self.password:
            logger.error("PM requires username and password.")
            return

        self.add_task(self._watch_pm())

    async def _watch_pm(self):
        pm = PM(self)
        self.pm = pm
        await pm.listen(self.username, self.password, reconnect=True)
        self.pm = None

    async def leave_pm(self):
        if self.pm:
            await self.pm.disconnect()

    def get_room(self, room_name: str):
        return self.rooms.get(room_name)

    def in_room(self, room_name: str):
        return room_name in self.rooms

    def join_room(self, room_name: str):
        if self.in_room(room_name):
            logger.error(f"Already joined room {room_name}")
            return

        self.add_task(self._watch_room(room_name))

    async def _watch_room(self, room_name: str):
        room = Room(self, room_name)
        self.rooms[room_name] = room
        await room.listen(self.username, self.password, reconnect=True)
        self.rooms.pop(room_name, None)

    async def leave_room(self, room_name: str):
        room = self.get_room(room_name)
        if room:
            await room.disconnect()


class OldClient(EventHandler):
    def __init__(self):
        self.pm = None
        self.user = None

        self._running = False
        self.silent = 2
        self._rooms = {}
        self.errors = []
        self.__rcopy = {}
        self._default_user_name = None
        self._default_password = None

    def __dir__(self):
        return [
            x
            for x in set(list(self.__dict__.keys()) + list(dir(type(self))))
            if x[0] != "_"
        ]

    async def join(self, room_name: str, anon=False) -> Optional[Room]:
        """
        @parasm room_name: str
        returns a Room object if roomname is valid
        else is going to return None
        """
        room_name = room_name.lower()
        expr = re.compile("^([a-z0-9-]{1,20})$")
        if not expr.match(room_name):
            return None
        if room_name in self._rooms:
            isconnected, canreconnect = self._rooms[room_name].check_connected()
            if not isconnected and canreconnect:
                await self.leave(room_name, True)
                self.check_rooms(room_name)
                await asyncio.sleep(0.2)
        room = Room(self, room_name)
        _accs = [
            self._default_user_name if not anon else "",
            self._default_password if not anon else "",
        ]
        await asyncio.wait_for(room.connect(*_accs), 6.0)

    async def leave(self, room_name: str, reconnect: bool):
        room_name = room_name.lower()
        if room_name not in self._rooms:
            return f"{False if NotConnectedError(room_name) else True}"
        # has to be in the dict until it's fully disconnected
        if room_name in self._rooms and self._rooms[room_name]._connection is not None:
            await self._rooms[room_name].cancel()
            if room_name in self._rooms:
                del self._rooms[room_name]
            await self._call_event("disconnect", room_name)
            if reconnect:
                if self._rooms[room_name].reconnect:
                    self.set_timeout(1, self.join, room_name)
            return True

    async def start(self, user=None, passwd=None, pm=None):
        self._running = True
        await self._call_event("init")
        if pm or self._default_pm == True:
            await self.pm_start(user, passwd)
        await self._call_event("start")
        self._reconnection = asyncio.create_task(self._while_rooms())

    async def _while_rooms(self):
        while True:
            await asyncio.sleep(1)
            for room in self._rooms:
                isconnected, canreconnect = self._rooms[room].check_connected()
                if canreconnect and not isconnected:
                    await self.leave(room, True)
            if not self._running:
                break

    async def pm_start(self, user=None, passwd=None):
        self.pm = PM(self)
        await self.pm.connect(
            user or self._default_user_name, passwd or self._default_password
        )

    @property
    def running(self):
        return self._running

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

    def default_user(
        self,
        user_name: str,
        password: Optional[str] = None,
        pm=True,
    ):
        self._default_user_name = user_name
        self._default_password = password
        self._default_pm = pm

    async def stop(self):
        self._reconnection.cancel()
        if self.pm and self.pm._connected == True:
            await self.pm.cancel()
            print(f"Disconnected from {self.pm}")
        for room in self.rooms:
            await self.leave(room.name, False)
        self._running = False

    async def enable_bg(self, active=True):
        """Enable background if available."""
        self.bgmode = active
        for room in self._rooms:
            await self._rooms[room].set_bg_mode(int(active))

    # async def upload_image(self, path, return_url=False):
    #     if self.user.isanon:
    #         return None
    #     with open(path, mode="rb") as f:
    #         files = {
    #             "filedata": {"filename": path, "content": f.read().decode("latin-1")}
    #         }
    #     data, headers = multipart(
    #         dict(u=self.client._default_user_name, p=self.client._default_password),
    #         files,
    #     )
    #     headers.update({"host": "chatango.com", "origin": "http://st.chatango.com"})
    #     async with get_aiohttp_session.post(
    #         "http://chatango.com/uploadimg",
    #         data=data.encode("latin-1"),
    #         headers=headers,
    #     ) as resp:
    #         response = await resp.text()
    #         if "success" in response:
    #             success = response.split(":", 1)[1]
    #     if success != None:
    #         if return_url:
    #             url = "http://ust.chatango.com/um/{}/{}/{}/img/t_{}.jpg"
    #             return url.format(
    #                 self.user.name[0], self.user.name[1], self.user.name, success
    #             )
    #         else:
    #             return f"img{success}"
    #     return None

    # def set_interval(self, tiempo, funcion, *args, **kwargs):
    #     """
    #     Llama a una función cada intervalo con los argumentos indicados
    #     @param funcion: La función que será invocada
    #     @type tiempo int
    #     @param tiempo:intervalo
    #     """
    #     task = Task(tiempo, funcion, True, *args, **kwargs)

    #     return task

    # def set_timeout(self, tiempo, funcion, *args, **kwargs):
    #     """
    #     Llama a una función cada intervalo con los argumentos indicados
    #     @param tiempo: Tiempo en segundos hasta que se ejecute la función
    #     @param funcion: La función que será invocada
    #     """
    #     task = Task(tiempo, funcion, False, *args, **kwargs)

    #     return task
