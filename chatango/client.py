import asyncio
import logging
from typing import Coroutine, Dict, List, Optional, Union
from asyncio import Future, Task

from .pm import PM
from .room import Room
from .handler import EventHandler
from .utils import public_attributes


logger = logging.getLogger(__name__)


class Client(EventHandler):
    def __init__(
        self, username: str = "", password: str = "", rooms: List[str] = [], pm=False
    ):
        self.running = False
        self.rooms: Dict[str, Room] = {}
        self.pm: Optional[PM] = None
        self.use_pm = pm
        self.initial_rooms: List[str] = rooms
        self.username = username
        self.password = password

        self._tasks: List[asyncio.Task] = []
        self._task_loops: List[asyncio.Task] = []


    def __dir__(self):
        return public_attributes(self)

  
    def add_task(self, coro_or_future: Union[Coroutine, Future]):# TODO
        task = asyncio.create_task(coro_or_future)
        self._handle_task(task)

    def _handle_task(self, task: Task):
        self._tasks.insert(0, task)

    def _prune_tasks(self):
        self._tasks = [task for task in self._tasks if not task.done()]

    async def _task_loop(self, forever=False):
        while self._tasks or forever:
            await asyncio.gather(*self._tasks)
            self._prune_tasks()
            if forever:
                await asyncio.sleep(0.1)

    async def run(self, *, forever=False):
        self.running = True
        await self._call_event("init")

        if not forever and not self.use_pm and not self.initial_rooms:
            logger.error("No rooms or PM to join. Exiting.")
            return

        if self.use_pm:
            self.join_pm()

        for room_name in self.initial_rooms:
            self.join_room(room_name)

        await self._call_event("start")
        await self._task_loop(forever)
        self.running = False

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

    def leave_pm(self):
        if self.pm:
            self.add_task(self.pm.disconnect())

    def get_room(self, room_name: str):
        Room.assert_valid_name(room_name)
        return self.rooms.get(room_name)

    def in_room(self, room_name: str):
        Room.assert_valid_name(room_name)
        return room_name in self.rooms

    def join_room(self, room_name: str):
        Room.assert_valid_name(room_name)
        if self.in_room(room_name):
            logger.error(f"Already joined room {room_name}")
            # Attempt to reconnect existing room?
            return

        self.add_task(self._watch_room(room_name))

    async def _watch_room(self, room_name: str):
        room = Room(self, room_name)
        self.rooms[room_name] = room
        await room.listen(self.username, self.password, reconnect=True)
        # Client level reconnect?
        self.rooms.pop(room_name, None)

    def leave_room(self, room_name: str):
        room = self.get_room(room_name)
        if room:
            self.add_task(room.disconnect())
            del self.rooms[room.name]

    async def stop(self):# this must be async
        if self.pm:
            await self.pm.disconnect()

        for room_name in self.rooms:
            room = self.get_room(room_name)
            await room.disconnect()

    async def enable_bg(self, active=True):
        """Enable background if available."""
        self.bgmode = active
        for _, room in self.rooms.items():
            await room.set_bg_mode(int(active))
