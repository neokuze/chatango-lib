
class BaseRoomError(Exception):
    room_name: str

    def __init__(self, room_name: str, room=None):
        super().__init__(room_name, room)
        self.room_name = room_name
        self.room = room


class AlreadyConnectedError(BaseRoomError):
    pass


class NotConnectedError(BaseRoomError):
    pass
