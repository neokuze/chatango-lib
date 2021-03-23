import asyncio

class BaseRoomError(Exception):
    room_name: str

    def __init__(self, room_name: str, room=None):
        super().__init__(room_name, room)
        self.room_name = room_name
        self.room = room


class AlreadyConnectedError(BaseRoomError):
    def __init__(self, room_name: str, room=None):
        super().__init__(room_name, room)
        self.room_name = room_name
        self.room = room

    def check(self):    
        return (self.room_name, self.room.connected, self.room.reconnect)

class NotConnectedError(BaseRoomError):
    room_name: str

    def __init__(self, room_name: str, room=None):
        super().__init__(room_name, room)
        self.room_name = room_name
        self.room = room

class WebSocketClosure(Exception):
    """
        trying to except when is closed.
    """
    pass