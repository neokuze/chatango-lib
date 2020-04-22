"""
Module for user related stuff
"""
import enum
import aiohttp, asyncio
from collections import deque
import json
import re, time
from .utils import make_requests

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


class User: #TODO a new format for users
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
        self._info = None
        self._client = None
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
        return "<User: %s>" % self.showname

    @property
    def get_user_dir(self):
        if not self.isanon:
            return '/%s/%s/' % ('/'.join((self.name * 2)[:2]), self.name)

    @property
    def fullpic(self):
        if not self.isanon:
            return f"http://fp.chatango.com/profileimg{self.get_user_dir}full.jpg"
        return False

    @property
    def msgbg(self):
        if not self.isanon:
            return f"http://fp.chatango.com/profileimg{self.get_user_dir}msgbg.jpg"
        return False

    @property
    def thumb(self):
        if not self.isanon:
            return f"http://fp.chatango.com/profileimg{self.get_user_dir}thumb.jpg"
        return False

    @property
    def name(self):
        return self._name

    @property
    def info(self):
        return self._info

    @property
    def blend_name(self):
        return self._blend_name

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
        if self._profile:
            return
        if not self.isanon:
            sites = [f"http://ust.chatango.com/profileimg{self.get_user_dir}msgstyles.json",
                f"http://ust.chatango.com/profileimg{self.get_user_dir}msgbg.xml",
                f"http://ust.chatango.com/profileimg{self.get_user_dir}mod1.xml",
            ]
            tasks = await make_requests(sites)
            result = [x.result() for x in tasks]
            resp = json.loads(result[0])
            self._nameColor, self._fontFace, self._fontSize, self._fontColor = resp["nameColor"], int(
                resp["fontFamily"]), int(resp["fontSize"]), resp["textColor"]
            self._usebackground = int(resp["usebackground"])
            bg = result[1].replace("<?xml version=\"1.0\" ?>", "")
            self._bgstyle = dict([url.replace('"', '').split(
                "=") for url in re.findall('(\w+=".*?")', bg)])
            text = result[2].replace("<?xml version=\"1.0\" ?>", "")
            self._profile = dict([url.replace('"', '').split(
                "=") for url in re.findall('(\w+=".*?")', text)[1:]])

    async def get_info(self):
        info = f'http://fp.chatango.com/profileimg{self.get_user_dir}mod2.xml'
        if not self._info and not self.isanon:
            task = await make_requests(info)
            print(task)
            self._info = task

class Styles:
    def __init__(self):
        self._nameColor = str("000000")
        self._fontColor = str("000000")
        self._fontSize = 11
        self._fontFace = 1
        self._usebackground = 0

        self._blend_name = None
        self._bgstyle = dict()
        self._profile = dict()

class Friend:
    _FRIENDS = dict()
    def __init__(self, user, client = None): 
        self.user = User(user)
        self.name = self.user.name
        self._client = client
        self._status = None
        self.idle = None
        self.last_active = None

    def  __repr__(self):
        if self.is_friend():
            return f"<Friend {self.name}>"
        return f"<User: {self.name}>"

    def __str__(self):
        return self.name

    @property
    def showname(self):
        return self.user.showname

    @property
    def client(self):
        return self._client

    @property
    def status(self):
        return self._status

    def is_friend(self):
        if self.client and not self.user.isanon:
            if self.name in self.client.friends:
                return True
            return False
        return None 

    async def friend_request(self):
        """
        Send a friend request
        """
        if self.is_friend() == False:
            return await self.client.add_friend(self.name)

    async def unfriend(self):
        """
        Delete friend
        """
        if self.is_friend() == True:
            return await self.client.unfriend(self.name)

    def is_online(self):
        return self.status == "online"

    def is_offline(self):
        return self.status in ["offline", "app"]
    
    def is_on_app(self):
        return self.status == "app"
    
    async def send_message(self, message):
        if self.client:
            await self.client.send_message(self.name, message)

    async def _check_status(self, _time=None, idle_time=None): # TODO
        """
        Check status:
        @parasm _time: time
        @parasm idle_time: time of user
        ##
        """
        if _time == None and idle_time == None or self.user.isanon:
            self.idle = None
            self.last_active = None
            return 
        if self.status == "on" and int(idle_time) >= 1:
            self.idle = True
            self.last_active = time.time() - (int(idle_time) * 60)
        else:
            self.idle = False
            self.last_active = float(_time)
