import asyncio
import aiohttp
import inspect

class Client:
    def __init__(self, aiohttp_session=None):
        if aiohttp_session is None:
            aiohttp_session = aiohttp.ClientSession() # mayormente no cierra
        self.aiohttp_session = aiohttp_session
        self.loop = self.aiohttp_session.loop
        self._rooms = dict()
        self.user = None
        self.debug = True # False

    def run(self, accounts = [("","")], rooms = ["pythonrpg"]):
        for room_name in rooms:
            self._rooms[room_name] = {} 
        # loop to rooms amd pv
        #start
        
    async def start(self):
        await self.on_init()

    async def stop(self):
        for room in self._rooms.values():
            await room.disconnect()
        self._rooms.clear()

    async def on_init(self):
        pass

    def event(self, func, name=None):
        assert inspect.iscoroutinefunction(func)
        if name is None:
            event_name = func.__name__
        else:
            event_name = name
        setattr(self, event_name, func)

