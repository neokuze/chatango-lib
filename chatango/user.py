"""
Module for user related stuff
"""
import enum
from collections import deque


class ModeratorFlags(enum.IntFlag):
    DELETED = 1 << 0
    EDIT_MODS = 1 << 1
    EDIT_MOD_VISIBILITY = 1 << 2
    EDIT_BW = 1 << 3
    EDIT_RESTRICTIONS = 1 << 4
    EDIT_GROUP = 1 << 5
    SEE_COUNTER = 1 << 6
    SEE_MOD_CHANNEL = 1 << 7
    SEE_MOD_ACTIONS = 1 << 8
    EDIT_NLP = 1 << 9
    EDIT_GP_ANNC = 1 << 10
    EDIT_ADMINS = 1 << 11
    EDIT_SUPERMODS = 1 << 12
    NO_SENDING_LIMITATIONS = 1 << 13
    SEE_IPS = 1 << 14
    CLOSE_GROUP = 1 << 15
    CAN_BROADCAST = 1 << 16
    MOD_ICON_VISIBLE = 1 << 17
    IS_STAFF = 1 << 18
    STAFF_ICON_VISIBLE = 1 << 19


AdminFlags = (ModeratorFlags.EDIT_MODS | ModeratorFlags.EDIT_RESTRICTIONS |
              ModeratorFlags.EDIT_GROUP | ModeratorFlags.EDIT_GP_ANNC)


class User:
    _users = {}

    def __new__(cls, name, **kwargs):
        key = name.lower()
        if key in cls._users:
            for attr, val in kwargs.items():
                if attr == 'ip' and not val:
                    continue  # only valid ips
                setattr(cls._users[key], '_' + attr, val)
            return cls._users[key]
        self = super().__new__(cls)

        cls._users[key] = self
        self._name = str()
        self._ip = None
        self._flags = 0
        self._history = deque(maxlen=5)
        self._isanon = False
        self._sids = dict()
        self._showname = str()
        self._ispremium = None

        for attr, val in kwargs.items():
            setattr(self, '_' + attr, val)
        return self

    def __repr__(self):
        return "<User: %s>" % self.name

    @property
    def name(self):
        return self._name
    @property
    def ispremium(self):
        return self._ispremium
    @property
    def showname(self):
        return self._showname

    @property
    def isanon(self):
        return self._isanon

    def setName(self, val):
        self._showname = val
        self._name = val.lower()

    def addSessionId(self, room, sid):
        if room not in self._sids:
            self._sids[room] = set()
        self._sids[room].add(sid)

    def removeSessionId(self, room, sid):
        if room in self._sids:
            if not sid:
                self._sids[room].clear()
            elif sid in self._sids[room]:
                self._sids[room].remove(sid)
            if len(self._sids[room]) == 0:
                del self._sids[room]
