"""
Module for room related stuff
"""

from .utils import gen_uid, getAnonName, _clean_message, _parseFont
from .connection import Connection
from .message import Message, MessageFlags
from .user import User, ModeratorFlags, AdminFlags
from collections import deque
import aiohttp
import asyncio
import sys
import typing
import html
import re
import time
import enum
import string

specials = {
    'mitvcanal': 56, 'animeultimacom': 34, 'cricket365live': 21,
    'pokemonepisodeorg': 22, 'animelinkz': 20, 'sport24lt': 56,
    'narutowire': 10, 'watchanimeonn': 22, 'cricvid-hitcric-': 51,
    'narutochatt': 70, 'leeplarp': 27, 'stream2watch3': 56, 'ttvsports': 56,
    'ver-anime': 8, 'vipstand': 21, 'eafangames': 56, 'soccerjumbo': 21,
    'myfoxdfw': 67, 'kiiiikiii': 21, 'de-livechat': 5, 'rgsmotrisport': 51,
    'dbzepisodeorg': 10, 'watch-dragonball': 8, 'peliculas-flv': 69,
    'tvanimefreak': 54, 'tvtvanimefreak': 54
}

# order matters
tsweights = [
    (5, 75), (6, 75), (7, 75), (8, 75), (16, 75), (17, 75), (18, 75), (9, 95),
    (11, 95), (12, 95), (13, 95), (14, 95), (15, 95), (19, 110), (23, 110),
    (24, 110), (25, 110), (26, 110), (28, 104), (29, 104), (30, 104),
    (31, 104), (32, 104), (33, 104), (35, 101), (36, 101), (37, 101),
    (38, 101), (39, 101), (40, 101), (41, 101), (42, 101), (43, 101),
    (44, 101), (45, 101), (46, 101), (47, 101), (48, 101), (49, 101),
    (50, 101), (52, 110), (53, 110), (55, 110), (57, 110), (58, 110),
    (59, 110), (60, 110), (61, 110), (62, 110), (63, 110), (64, 110),
    (65, 110), (66, 110), (68, 95), (71, 116), (72, 116), (73, 116), (74, 116),
    (75, 116), (76, 116), (77, 116), (78, 116), (79, 116), (80, 116),
    (81, 116), (82, 116), (83, 116), (84, 116)
]


class RoomFlags(enum.IntFlag):
    LIST_TAXONOMY = 1 << 0
    NO_ANONS = 1 << 2
    NO_FLAGGING = 1 << 3
    NO_COUNTER = 1 << 4
    NO_IMAGES = 1 << 5
    NO_LINKS = 1 << 6
    NO_VIDEOS = 1 << 7
    NO_STYLED_TEXT = 1 << 8
    NO_LINKS_CHATANGO = 1 << 9
    NO_BROADCAST_MSG_WITH_BW = 1 << 10
    RATE_LIMIT_REGIMEON = 1 << 11
    CHANNELS_DISABLED = 1 << 13
    NLP_SINGLEMSG = 1 << 14
    NLP_MSGQUEUE = 1 << 15
    BROADCAST_MODE = 1 << 16
    CLOSED_IF_NO_MODS = 1 << 17
    IS_CLOSED = 1 << 18
    SHOW_MOD_ICONS = 1 << 19
    MODS_CHOOSE_VISIBILITY = 1 << 20
    NLP_NGRAM = 1 << 21
    NO_PROXIES = 1 << 22
    HAS_XML = 1 << 28
    UNSAFE = 1 << 29


def get_server(group):
    """
    Get the server host for a certain room.

    @type group: str
    @param group: room name

    @rtype: str
    @return: the server's hostname
    """
    try:
        sn = specials[group]
    except KeyError:
        group = group.replace("_", "q")
        group = group.replace("-", "q")
        fnv = int(group[:5], 36)
        lnv = group[6:9]
        if lnv:
            lnv = int(lnv, 36)
            lnv = max(lnv, 1000)
        else:
            lnv = 1000
        num = (fnv % lnv) / lnv
        maxnum = sum(y for x, y in tsweights)
        cumfreq = 0
        sn = 0
        for x, y in tsweights:
            cumfreq += float(y) / maxnum
            if num <= cumfreq:
                sn = x
                break
    return f"s{sn}.chatango.com"


class Room(Connection):
    def __new__(cls, client, name: str):
        name = name.lower()
        if name not in client._rooms:
            self = super(Room, cls).__new__(cls)
            cls.__init__(self, client, name)
            client._rooms[name] = self
        return client._rooms[name]

    def __init__(self, client, name: str):
        if name in client._rooms:
            return 
        super().__init__(client)
        self.name = name
        self.server = get_server(name)
        self._uid = gen_uid()
        self._user = None
        self._owner = None
        self._mods = dict()
        self._userhistory = deque(maxlen=10)
        self._userdict = dict()
        self._mqueue = dict()
        self._msgs = dict()
        self._users = dict()
        self._unbanqueue = deque(maxlen=500)
        self._unid = str()
        self._usercount = 0
        self._maxlen = 2900
        self._history = deque(maxlen=self._maxlen)
        self._bgmode = 1
        self.message_flags = 0

    def __repr__(self):
        return f"<Room {self.name}, {f'connected as {self._user}' if self.connected else 'not connected'}>"

    @property
    def owner(self):
        return self._owner

    @property
    def user(self):
        return self._user

    @property
    def mods(self):
        return set(self._mods.keys())

    @property
    def userlist(self):
        return self._getUserlist()

    @property
    def anonlist(self):
        """Lista de anons detectados"""
        return list(set(self.alluserlist) - set(self.userlist))

    @property
    def usercount(self):  # TODO
        """Len users -> user count"""
        return self._usercount

    @property
    def alluserlist(self):
        """Lista de todos los usuarios en la sala (con anons)"""
        return sorted([x[1] for x in list(self._userdict.values())],
                      key=lambda z: z.name.lower())

    def setFont(self, attr, font):
        if attr == "namecolor":
            self._user._nameColor = str(font)
        elif attr == "fontcolor":
            self._user._fontColor = str(font)
        elif attr == "fontsize":
            self._user._fontSize = int(font)
        elif attr == "fontface":
            self._user._fontFace = int(font)

    async def setBgMode(self, mode):
        self._bgmode = mode
        if self.connected and self.user.ispremium:
            await self._send_command('msgbg', str(self._bgmode))

    def getSessionlist(self, mode=0, memory=0):  # TODO
        if mode < 2:
            return [(x.name if mode else x, len(x.getSessionIds(self))) for x in
                    self._getUserlist(1, memory)]
        else:
            return [(x.showname, len(x.getSessionIds(self))) for x in
                    self._getUserlist(1, memory)]

    def _getUserlist(self, unique=1, memory=0, anons=False):
        ul = []
        if not memory:
            ul = [x[1] for x in self._userdict.copy().values() if
                  anons or not x[1].isanon]
        elif type(memory) == int:
            ul = set(map(lambda x: x.user, list(self._history)[
                min(-memory, len(self._history)):]))
        if unique:
            ul = set(ul)
        return sorted(list(ul), key=lambda x: x.name.lower())

    def getLevel(self, user):
        if isinstance(user, str):
            user = User(user)
        if user == self._owner:
            return 3
        if user in self._mods:
            if self._mods.get(user).isadmin:
                return 2
            else:
                return 1
        return 0

    def _addHistory(self, msg):
        pass

    async def _reload(self):
        if self._usercount <= 1000:
            await self._send_command("g_participants:start")
        else:
            await self._send_command("gparticipants:start")
        await self._send_command("getpremium", "l")
        await self._send_command('getannouncement')
        await self._send_command("getbannedwords")
        await self._send_command("getratelimit")

    async def _disconnect(self):
        for x in self.userlist:
            x.removeSessionId(self, 0)

    async def _connect(self, user_name: typing.Optional[str] = None, password: typing.Optional[str] = None):
        self._user = user_name
        self._connection = await self.client.aiohttp_session.ws_connect(
            f"ws://{self.server}:8080/",
            origin="http://st.chatango.com"
        )
        await self._send_command("bauth", self.name, self._uid, user_name or "", password or "")

    async def send_message(self, message, use_html=False):
        message_flags = str(self.message_flags) or "0"
        name_color = self.user._nameColor or str("000000")
        font_size = self.user._fontSize or 12
        font_face = self.user._fontFace or 0
        font_color = self.user._fontColor or str("000000")
        message = str(message)
        if not use_html:
            message = html.escape(message, quote=False)
        message = f'<n{name_color}/><f x{font_size}{font_color}="{font_face}">{message}</f>'
        await self._send_command("bm", "chlb", message_flags, message)

    async def _rcmd_ok(self, args):  # TODO
        self._owner = User(args[0])
        self._puid = args[1]
        self._currentname = args[3]
        self._connectiontime = args[4]
        self._correctiontime = int(float(self._connectiontime) - time.time())
        self._currentIP = args[5]
        self._login_as = args[2]
        self._flags = RoomFlags(int(args[7]))
        if self._login_as == 'C':
            self._user = User(getAnonName(self._puid, str(
                self._connectiontime)), isanon=True, ip=self._currentIP)
        elif self._login_as == 'M':
            self._user = User(self._currentname,
                              puid=self._puid, ip=self._currentIP)
        self._user.setName(self._currentname)
        for mod in args[6].split(";"):
            if len(mod.split(",")) > 1:
                mod, power = mod.split(",")
                self._mods[User(mod)] = ModeratorFlags(int(power))
                self._mods[User(mod)].isadmin = ModeratorFlags(int(
                    power)) & AdminFlags != 0
        await self.client._call_event("room_init", self)

    async def _rcmd_inited(self, args):
        await self._reload()

    async def _rcmd_pong(self, args):
        await self.client._call_event(self, "pong")

    async def _rcmd_nomore(self, args):  # TODO
        """No more past messages"""
        pass

    async def _rcmd_n(self, args):
        """user count"""
        self._usercount = int(args[0], 16)

    async def _rcmd_i(self, args):
        """history past messages"""
        # TODO: Proper handling
        await self._rcmd_b(args)

    async def _rcmd_b(self, args):  # TODO
        """Process message"""
        _time = float(args[0]) - 0
        name, tname, puid, unid, msgid, ip, flags = args[1:8]
        body = ":".join(args[9:])
        msg = Message()
        msg._room = self
        msg._time = float(_time)
        msg._puid = str(puid)
        msg._tempname = tname
        msg._msgid = msgid
        msg._unid = unid
        msg._ip = ip
        msg._body = html.unescape(
            re.sub("<(.*?)>", "", body.replace("<br/>", "\n"))
        )
        body, n, f = _clean_message(body)
        isanon = False
        if not name:
            if not tname:
                if n.isdigit():
                    name = getAnonName(puid, n)
                elif n and all(x in string.hexdigits for x in n):
                    name = getAnonName(puid, str(int(n, 16)))
                else:
                    name = getAnonName(puid, None)
            else:
                name = tname
            isanon = True
        else:
            if n:
                msg._nameColor = n
            else:
                msg._nameColor = None
        msg._user = User(name, ip=ip, isanon=isanon)
        msg._fontSize, msg._fontColor, msg._fontFace = _parseFont(f.strip())
        msg._user.setName(name)
        msg._flags = MessageFlags(int(flags))
        ispremium = MessageFlags.PREMIUM in msg._flags
        if msg._user.ispremium != ispremium:
            evt = msg._user._ispremium != None and ispremium != None and _time > time.time() - 5
            msg._user._ispremium = ispremium
            if evt:
                await self.client._call_event("premium_change", msg._user, ispremium)
        self._mqueue[msg._msgid] = msg

    async def _rcmd_premium(self, args):  # TODO
        # print
        if self._bgmode and (args[0] == '210' or (
                isinstance(self, Room) and self._owner == self.user)):
            await self._send_command('msgbg', str(self._bgmode))

    async def _rcmd_show_fw(self, args=None):
        await self.client._call_event('flood_warning')

    async def _rcmd_u(self, args):
        """attachs and call event on_message"""
        if args[0] in self._mqueue:
            msg = self._mqueue.pop(args[0])
            if msg._user != self._user:
                pass
            msg.attach(self, args[1])
            await self.client._call_event("message", msg)

    async def _rcmd_gparticipants(self, args):
        """old command, chatango keep sending it."""
        await self._rcmd_g_participants(len(args) > 1 and args[1:] or '')

    async def _rcmd_g_participants(self, args):
        self._userdict = dict()
        args = ':'.join(args).split(";")
        if not args or not args[0]:
            return  # Fix
        for data in args:
            data = data.split(':')  # Lista de un solo usuario
            ssid = data[0]
            contime = data[1]  # Hora de conexión a la sala
            puid = data[2]
            name = data[3]
            tname = data[4]
            isanon = False
            if name == 'None':
                isanon = True
                if tname != 'None':
                    name = tname
                else:
                    name = getAnonName(puid, contime)
            user = User(name, isanon=isanon, puid=puid)
            if user in ({self._owner} | self.mods):
                user.setName(name)
            user.addSessionId(self, ssid)
            self._userdict[ssid] = [contime, user]

    async def _rcmd_participant(self, args):
        cambio = args[0]  # Leave Join Change
        ssid = args[1]  # session
        puid = args[2]  # UID
        name = args[3]  # username
        tname = args[4]  # Anon Name
        unknown = args[5]  # ip
        contime = args[6]  # time
        isanon = False
        if name == 'None':
            if tname != 'None':
                name = tname
            else:
                name = getAnonName(puid, contime)
            isanon = True
        user = User(name, isanon=isanon, puid=puid, ip=unknown)
        user.setName(name)
        before = None
        if ssid in self._userdict:
            before = self._userdict[ssid][1]
        if cambio == '0':  # Leave
            user.removeSessionId(self, ssid)
            if ssid in self._userdict:
                usr = self._userdict.pop(ssid)[1]
                lista = [x[1] for x in self._userhistory]
                if usr not in lista:
                    self._userhistory.append([contime, usr])
                else:
                    self._userhistory.remove(
                        [x for x in self._userhistory if x[1] == usr][0])
                    self._userhistory.append([contime, usr])
            if user.isanon:
                await self.client._call_event('anonleave', user, puid)
            else:
                await self.client._call_event('leave', user, puid)
        elif cambio == '1' or not before:  # Join
            user.addSessionId(self, ssid)
            if not user.isanon and user not in self.userlist:
                await self.client._call_event('join', user, puid)
            elif user.isanon:
                await self.client._call_event('anonjoin', user, puid)
            self._userdict[ssid] = [contime, user]
            lista = [x[1] for x in self._userhistory]
            if user in lista:
                self._userhistory.remove(
                    [x for x in self._userhistory if x[1] == user][0])
        else:  # TODO
            if before.isanon:  # Login
                if user.isanon:
                    await self.client._call_event('anonlogin', user, puid)
                else:
                    await self.client._call_event('userlogin', user, puid)
            elif not before.isanon:  # Logout
                if before in self.userlist:
                    lista = [x[1] for x in self._userhistory]

                    if before not in lista:
                        self._userhistory.append([contime, before])
                    else:
                        lst = [x for x in self._userhistory if before == x[1]]
                        if lst:
                            self._userhistory.remove(lst[0])
                        self._userhistory.append([contime, before])
                    await self.client._call_event('userlogout', before, puid)
            self._userdict[ssid] = [contime, user]
