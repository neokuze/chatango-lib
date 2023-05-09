class BaseRoomError(Exception):
    room_name: str

    def __init__(self, room_name: str):
        super().__init__(room_name)
        self.room_name = room_name


class AlreadyConnectedError(BaseRoomError):
    pass


class NotConnectedError(BaseRoomError):
    pass


class InvalidRoomNameError(BaseRoomError):
    pass
