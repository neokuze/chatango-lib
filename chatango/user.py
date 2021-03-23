"""
Module for user related stuff
"""
import enum
import aiohttp
import asyncio
import json
import urllib
import re
import time
import html
import datetime
from collections import deque
from .utils import Styles, _convert_dict


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


class User:  # TODO a new format for users
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
        self._styles = Styles()
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
    def age(self):
        return self.styles._profile['about']['age']

    @property
    def last_change(self):
        return self.styles._profile['about']['last_change']

    @property
    def gender(self):
        return self.styles._profile['about']['gender']

    @property
    def location(self):
        return self.styles._profile['about']['location']

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
    def styles(self):
        return self._styles

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
    def _links(self):
        return [["msgstyles", f"{self._ust}{self.get_user_dir}msgstyles.json"],
                ["msgbg", f"{self._ust}{self.get_user_dir}msgbg.xml"],
                ["mod1", f"{self._ust}{self.get_user_dir}mod1.xml"],
                ["mod2", f"{self._ust}{self.get_user_dir}mod2.xml"]]

    @property
    def isanon(self):
        return self._isanon

    def setName(self, val):
        self._showname = val
        self._name = val.lower()

    def del_profile(self):
        if self.styles.profile:
            del self._styles._profile
            self._styles._profile.update(dict(about={}, full={}))

    def addSessionId(self, room, sid):
        if room not in self._sids:
            self._sids[room] = set()
        self._sids[room].add(sid)

    def getSessionIds(self, room=None):
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

    async def get_profile(self):
        if self.isanon:
            return
        result = await self.__get_prof()
        self._styles._bgstyle = result['msgbg']
        self._styles._profile['about'] = result['mod1']
        self._styles._profile['full'] = result['mod2']

    def __links(self, user_dir):
        directory = '/%s/%s/' % ('/'.join((user_dir * 2)[:2]), user_dir)
        url = "http://ust.chatango.com/profileimg"
        urls = [
            ['msgstyles', f"{url}{directory}msgstyles.json"],
            ['msgbg', f"{url}{directory}msgbg.xml"],
            ['mod1', f"{url}{directory}mod1.xml"],
            ['mod2', f"{url}{directory}mod2.xml"]]
        return urls

    async def __get_prof(self):
        result = {}
        for ph in self.__links(self.name):
            async with aiohttp.ClientSession() as session:
                async with session.get(ph[1]) as response:
                    r = None
                    _src = await response.read()
                    try:
                        src = str(_src, 'utf-8')
                    except:
                        if ph[0] == "mod2":
                            src = dict(about=dict(), full=dict())
                    if ph[0] == "msgstyles":
                        jp = json.loads(src)
                        r = self._styles = Styles(font_face=jp['fontFamily'],
                                                  name_color=jp['nameColor'],
                                                  font_color=jp['textColor'],
                                                  font_size=jp['fontSize'],
                                                  use_background=jp["usebackground"]
                                                  )

                    elif ph[0] == "msgbg":
                        position = dict(tl='top left', tr='top right',
                                        bl='bottom left', br='bottom right')
                        r = dict([url.replace('"', '').split("=")
                                  for url in re.findall('(\w+=".*?")', src)])
                        if "fontFamily" in src: # No bg in account / maybe a bug  #TODO
                            r = {'align': 'None', 'bgalp': 'None', 'bgc': 'None',
                             'hasrec': 'None', 'ialp': 'None',
                             'isvid': 'None', 'tile': 'None', 'useimg': 'None'}
                        else:
                            r.update({'align': position[r['align']]})

                    elif ph[0] == "mod1":
                        wtt = dict(l="location", body="body",
                                   d="d", b="last_change", s="gender")
                        prof = dict(age='?')
                        for tag in list(wtt.keys()):
                            try:
                                if tag == "l":
                                    if len(src.split("<l")) > 1:
                                        r = src.split("<l")[1].split(
                                            ">", 1)[1].split("</l>")[0]
                                elif tag == "s":
                                    r = src.split("<s>")[1].split('<')[0] if len(
                                        src.split("<s>")) > 1 else '?'
                                elif tag == "b":
                                    r = src.split('<b>')[1].split('</b>')[0]
                                    if r:
                                        prof['age'] = abs(
                                            datetime.datetime.now().year-int(r.split('-')[0]))
                                else:
                                    _r = re.findall(
                                        r"((?:<{0}>)+)([^>].*?[^<])((?:</{0}>)+)".format(tag), src)
                                    if isinstance(_r, type([])):
                                        r = _r[0][1] if _r else ""
                            except:
                                pass
                            prof[wtt[tag]] = r
                        r = prof

                    elif ph[0] == "mod2":
                        if src and "<body>" in src:
                            r = src.split("<body>")[1].split('</body>')[0]
                    result[ph[0]] = r
        return result


class Friend:
    _FRIENDS = dict()

    def __init__(self, user, client=None):
        self.user = user
        self.name = user.name
        self._client = client

        self._status = None
        self._idle = None
        self._last_active = None

    def __repr__(self):
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

    @ property
    def showname(self):
        return self.user.showname

    @ property
    def client(self):
        return self._client

    @ property
    def status(self):
        return self._status

    @ property
    def last_active(self):
        return self._last_active

    @ property
    def idle(self):
        return self._idle

    def is_friend(self):
        if self.client and not self.user.isanon:
            if self.name in self.client.friends:
                return True
            return False
        return None

    async def send_friend_request(self):
        """
        Send a friend request
        """
        if self.is_friend() == False:
            return await self.client.addfriend(self.name)

    async def unfriend(self):
        """
        Delete friend
        """
        if self.is_friend() == True:
            return await self.client.unfriend(self.name)

    @ property
    def is_online(self):
        return self.status == "online"

    @ property
    def is_offline(self):
        return self.status in ["offline", "app"]

    @ property
    def is_on_app(self):
        return self.status == "app"

    async def reply(self, message):
        if self.client:
            await self.client.send_message(self.name, message)

    def _check_status(self, _time=None, _idle=None, idle_time=None):  # TODO
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
