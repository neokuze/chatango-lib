"""
Module for user related stuff
"""
import enum
import aiohttp, asyncio
from collections import deque
import json
import re, time, html
from .utils import make_requests
import datetime

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
        self._client = None
        self._last_time = None
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
            return f"{self._fp}{self.get_user_dir}full.jpg"
        return False

    @property
    def last_time(self):
        return self._last_time

    @property
    def msgbg(self):
        if not self.isanon:
            return f"{self._fp}{self.get_user_dir}msgbg.jpg"
        return False

    @property
    def thumb(self):
        if not self.isanon:
            return f"{self._fp}{self.get_user_dir}thumb.jpg"
        return False

    @property
    def _fp(self):
        return "http://fp.chatango.com/profileimg"

    @property
    def _ust(self):
        return "http://ust.chatango.com/profileimg"

    @property
    def name(self):
        return self._name

    @property
    def blend_name(self):
        return self._blend_name

    @property
    def puid(self):
        return self._puid

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
    def _links(self):
        return [["msgstyles", f"{self._ust}{self.get_user_dir}msgstyles.json"],
                ["msgbg", f"{self._ust}{self.get_user_dir}msgbg.xml"],
                ["mod1", f"{self._ust}{self.get_user_dir}mod1.xml"],
                ["mod2", f"{self._ust}{self.get_user_dir}mod2.xml"]]
    @property
    def aboutme(self):
        return self.profile["about"]

    @property
    def main_profile(self):
        return self.profile["full"]

    @property
    def isanon(self):
        return self._isanon

    def setName(self, val):
        self._showname = val
        self._name = val.lower()

    def del_profile(self):
        if self._profile:
            del self._profile
            self._profile.update(dict(about={}, full={}))

    def addSessionId(self, room, sid):
        if room not in self._sids:
            self._sids[room] = set()
        self._sids[room].add(sid)


    def getSessionIds(self, room = None):
        if room:
            return self._sids.get(room, set())
        else:
            return set.union(*self._sids.values())

    def removeSessionId(self, room, sid):
        if room in self._sids:
            if not sid:
                self._sids[room].clear()
            elif sid in self._sids[room]:
                self._sids[room].remove(sid)
            if len(self._sids[room]) == 0:
                del self._sids[room]

    async def get_styles(self):
        if not self.isanon:
            tasks = await make_requests(self._links[:2])
            msgs = tasks["msgstyles"].result()
            msgbg = tasks["msgbg"].result()
            dstyles = json.loads(msgs)
            bg = msgbg.replace("<?xml version=\"1.0\" ?>", "")
            self._nameColor, self._fontFace = dstyles["nameColor"], int(dstyles["fontFamily"])
            self._fontSize, self._fontColor = int(dstyles["fontSize"]), dstyles["textColor"]
            self._usebackground = int(dstyles["usebackground"])
            self._bgstyle = dict([url.replace('"', '').split("=") for url in re.findall('(\w+=".*?")', bg)])
            position = dict(tl='top left', tr='top right', bl='bottom left', br='bottom right')
            self._bgstyle["align"] = position[self._bgstyle["align"]]
            
    async def get_main_profile(self):
        if self._profile['about']:
            return
        if not self.isanon:
            tasks = await make_requests(self._links[2:])
            about = tasks["mod1"].result()
            about = about.replace("<?xml version=\"1.0\" ?>", "")
            body = about.split("<body>")[1].split("</body>")[0].replace("%20", " ").replace("\n", " ")
            gender = about.split("<s>")[1].split("</s>")[0]
            location = about.split("<l")[1].split(">",1)[1].split("</l>")[0]
            last_change = ""
            age = ""
            d = ""
            if len(about.split("<b>")) >1:
                last_change = about.split("<b>")[1].split("</b>")[0]
            if last_change != "":
                age = abs(datetime.datetime.now().year-int(last_change.split("-")[0]))
            if len(about.split("<d>")) >1:
                d = about.split("<d>")[1].split("</d>")[0]
            self._profile["about"] = dict(age=age, last_change=last_change ,gender=gender or '?',location=location, d=d, mini=body)
            try:
                fullprof = tasks["mod2"].result()
                if fullprof is not None and str(fullprof)[:5] == "<?xml":
                    self._profile["full"] = html.unescape(fullprof.split("<body",1)[1].split(">",1)[1].split("</body>",1)[0]).replace("%20", " ").replace("\n", " ")
            except:
                pass

class Styles:
    def __init__(self):
        self._nameColor = str("000000")
        self._fontColor = str("000000")
        self._fontSize = 11
        self._fontFace = 1
        self._usebackground = 0

        self._blend_name = None
        self._bgstyle = dict()
        self._profile = dict(about=dict(), full=dict())

class Friend:
    _FRIENDS = dict()
    
    def __init__(self, user, client = None): 
        self.user = user
        self.name = user.name
        self._client = client

        self._status = None
        self._idle = None
        self._last_active = None
        
    def  __repr__(self):
        if self.is_friend():
            return f"<Friend {self.name}>"
        return f"<User: {self.name}>"

    def __str__(self):
        return self.name

    def get(name):
        return Friend._FRIENDS.get(name) or Friend(name)

    def __dir__(self):
        return [x for x in
                set(list(self.__dict__.keys()) + list(dir(type(self)))) if
                x[0] != '_']
    @property
    def showname(self):
        return self.user.showname

    @property
    def client(self):
        return self._client

    @property
    def status(self):
        return self._status

    @property
    def last_active(self):
        return self._last_active

    @property
    def idle(self):
        return self._idle

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

    @property
    def is_online(self):
        return self.status == "online"

    @property
    def is_offline(self):
        return self.status in ["offline", "app"]
    
    @property
    def is_on_app(self):
        return self.status == "app"
    
    async def reply(self, message):
        if self.client:
            await self.client.send_message(self.name, message)

    def _check_status(self, _time=None, _idle=None, idle_time=None): # TODO
        if _time == None and idle_time == None:
            self.last_active = None
            return 
        if _idle != None:
            self._idle = _idle
        if self.status == "online" and int(idle_time) >= 1:
            self._last_active = time.time() - (int(idle_time) * 60)
            self._idle = True
        else:
            self._last_active = float(_time)
