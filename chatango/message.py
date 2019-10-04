import html
import re
import enum


class MessageFlags(enum.IntFlag):
    PREMIUM = 1 << 2
    BG_ON = 1 << 3
    MEDIA_ON = 1 << 4
    CENSORED = 1 << 5
    SHOW_MOD_ICON = 1 << 6
    SHOW_STAFF_ICON = 1 << 7
    DEFAULT_ICON = 1 << 6
    CHANNEL_RED = 1 << 8
    CHANNEL_ORANGE = 1 << 9
    CHANNEL_GREEN = 1 << 10
    CHANNEL_CYAN = 1 << 11
    CHANNEL_BLUE = 1 << 12
    CHANNEL_PURPLE = 1 << 13
    CHANNEL_PINK = 1 << 14
    CHANNEL_MOD = 1 << 15


class Message(object):
    def __init__(self):
        self._msgid = None
        self._user = None
        self._room = None
        self._nameColor = str("000000")
        self._fontColor = str("000000")
        self._fontSize = 12
        self._fontFace = 0
        self._time = 0
        self._puid = int()
        self._body = str()
        self._ip = str()
        self._unid = str()
        self._flags = dict()

    @property
    def user(self):
        return self._user
        
    @property
    def body(self):
        return str(self._body) # ensure str

    @property
    def time(self):
        return self._time
    
    @property
    def flags(self):
        return self._flags

    @property
    def ip(self):
        return self._ip

    @property
    def room(self):
        return self._room

    def attach(self, room, msgid):
        if self._msgid is not None:
            self._room = room
            self._msgid = msgid
            self._room._msgs.update({msgid: self})

    def detach(self):
        if self._msgid is not None and self._msgid in self._room._msgs:
            self._room._msgs.pop(self._msgid)
