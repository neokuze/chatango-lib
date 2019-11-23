"""
Module for user related stuff
"""
import enum
import aiohttp
from collections import deque
import json
import re


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
        Styles.__init__(self)
        cls._users[key] = self
        self._name = name.lower()
        self._ip = None
        self._flags = 0
        self._history = deque(maxlen=5)
        self._isanon = False
        self._sids = dict()
        self._showname = name
        self._ispremium = None
        self._puid = str()
        for attr, val in kwargs.items():
            setattr(self, '_' + attr, val)
        return self
    
    def get(name):
        return User._users.get(name) or User(name)
    
    def __dir__(self):
        return [x for x in
                set(list(self.__dict__.keys()) + list(dir(type(self)))) if
                x[0] != '_']
    def __repr__(self):
        return "<User: %s>" % self.name

    @property
    def fullpic(self):
        if not self.isanon:
            link = '/%s/%s/' % ('/'.join((self.name * 2)[:2]), self.name)
            fp = f"http://fp.chatango.com/profileimg{link}full.jpg"
            return fp
        return False

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
    def default(self):
        size = str(self._fontSize)
        face = str(self._fontFace)
        return f"<f x{size}{self._fontColor}='{face}'>"

    @property
    def profile(self):
        return self._profile

    @property
    def bgstyle(self):
        return self._bgstyle

    @property
    def bg_on(self):
        return int(self._usebackground)
        
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

    async def get_profile(self):
        if not self.isanon:
            link = '/%s/%s/' % ('/'.join((self.name * 2)[:2]), self.name)
            async with aiohttp.ClientSession() as session:
                if self._no_refresh == False:
                    self._no_refresh = True
                    async with session.get(f"http://ust.chatango.com/profileimg{link}msgstyles.json") as resp:
                        resp = json.loads(await resp.text())
                        self._nameColor, self._fontFace, self._fontSize, self._fontColor = resp["nameColor"], int(
                            resp["fontFamily"]), int(resp["fontSize"]), resp["textColor"]
                        self._usebackground = int(resp["usebackground"])

                    async with session.get(f"http://ust.chatango.com/profileimg{link}msgbg.xml") as resp:
                        text = await resp.text()
                        text = text.replace("<?xml version=\"1.0\" ?>", "")
                        self._bgstyle = dict([url.replace('"', '').split(
                            "=") for url in re.findall('(\w+=".*?")', text)])

                    async with session.get(f"http://ust.chatango.com/profileimg{link}mod1.xml") as resp:
                        text = await resp.text()
                        text = text.replace("<?xml version=\"1.0\" ?>", "")
                        self._profile = dict([url.replace('"', '').split(
                            "=") for url in re.findall('(\w+=".*?")', text)[1:]])


class Styles:
    def __init__(self):
        self._nameColor = str("000000")
        self._fontColor = str("000000")
        self._fontSize = 11
        self._fontFace = 1
        self._usebackground = 0

        self._no_refresh = False
        self._bgstyle = dict()
        self._profile = dict()


