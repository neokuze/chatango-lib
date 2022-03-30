"""
Module for room related stuff
"""

from .utils import gen_uid, get_anon_name, _clean_message, _parseFont, _id_gen, multipart, _account_selector
from .connection import Connection
from .message import Message, MessageFlags, _process, mentions, message_cut
from .user import User, ModeratorFlags, AdminFlags
from collections import deque, namedtuple
from .utils import get_token, gen_uid
import aiohttp
import asyncio
import sys
import typing
import html
import re
import time
import enum
import string
import random
import urllib.request as urlreq

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
    [5, 75], [6, 75], [7, 75], [8, 75], [16, 75],
    [17, 75], [18, 75], [9, 95], [11, 95], [12, 95],
    [13, 95], [14, 95], [15, 95], [19, 110], [23, 110],
    [24, 110], [25, 110], [26, 110], [28, 104], [29, 104],
    [30, 104], [31, 104], [32, 104], [33, 104], [35, 101],
    [36, 101], [37, 101], [38, 101], [39, 101], [40, 101],
    [41, 101], [42, 101], [43, 101], [44, 101], [45, 101],
    [46, 101], [47, 101], [48, 101], [49, 101], [50, 101],
    [52, 110], [53, 110], [55, 110], [57, 110],
    [58, 110], [59, 110], [60, 110], [61, 110],
    [62, 110], [63, 110], [64, 110], [65, 110],
    [66, 110], [68, 95], [71, 116], [72, 116],
    [73, 116], [74, 116], [75, 116], [76, 116],
    [77, 116], [78, 116], [79, 116], [80, 116],
    [81, 116], [82, 116], [83, 116], [84, 116]
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
    UPDATED = 1 << 12
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
    _BANDATA = namedtuple('BanData', ['unid', 'ip', 'target', 'time', 'src'])

    def __new__(cls, client, name: str):
        name = name.lower()
        if name not in client._rooms:
            self = super(Room, cls).__new__(cls)
            cls.__init__(self, client, name)
            client._rooms[name] = self
        return client._rooms[name]

    def __dir__(self):
        return [x for x in
                set(list(self.__dict__.keys()) + list(dir(type(self)))) if
                x[0] != '_']

    def __init__(self, client, name: str):
        if name in client._rooms:
            return
        super().__init__(client)
        self.name = name
        self.server = get_server(name)
        self._uid = gen_uid()
        self._bwqueue = str()
        self._user = None
        self._silent = False
        self._owner = None
        self._mods = dict()
        self._userhistory = deque(maxlen=10)
        self._userdict = dict()
        self._mqueue = dict()
        self._msgs = dict()
        self._users = dict()
        self._unid = str()
        self._banlist = dict()
        self._unbanlist = dict()
        self._unbanqueue = deque(maxlen=500)
        self._usercount = 0
        self._del_dict = dict()
        self._maxlen = 2700
        self._BigMessageCut=False
        self._history = deque(maxlen=self._maxlen+300)
        self._bgmode = 0
        self._reconnect = True
        self._nomore = False
        self._connectiontime = None
        self.message_flags = 0
        self._announcement = [0, 0, '']
        self._badge = 0
        self._connected = None

    def __repr__(self):
        return f"<Room {self.name}, {f'connected as {self._user}' if self.connected else 'not connected'}>"

    @property
    def is_pm(self):
        return False

    @property
    def badge(self):
        if not self._badge:
            return 0
        elif self._badge == 1:
            return MessageFlags.SHOW_MOD_ICON.value
        elif self._badge == 2:
            return MessageFlags.SHOW_STAFF_ICON.value
        else:
            return 0

    @property
    def change_reconnect(self):
        if self.reconnect == True:
            self._reconnect = False
        else:
            self._reconnect = True
        return self.reconnect

    @property
    def reconnect(self):
        return self._reconnect

    @property
    def unbanlist(self):
        """Lista de usuarios desbaneados"""
        return list(set(x.target.name for x in self._unbanqueue))

    @property
    def history(self):
        return self._history

    @property
    def silent(self):
        return self._silent

    @property
    def banlist(self):
        return list(self._banlist.keys())

    @property
    def owner(self):
        return self._owner

    @property
    def flags(self):
        return self._flags

    @property
    def user(self):
        return self._user

    @property
    def mods(self):
        return set(self._mods.keys())

    @property
    def userlist(self):
        return self._get_user_list()

    @property
    def anonlist(self):
        """Lista de anons detectados"""
        return list(set(self.alluserlist) - set(self.userlist))

    @property
    def usercount(self):  # TODO
        """Len users -> user count"""
        if RoomFlags.NO_COUNTER in self.flags:
            return len(self.alluserlist)
        return self._usercount

    @property
    def alluserlist(self):
        """Lista de todos los usuarios en la sala (con anons)"""
        return sorted([x[1] for x in list(self._userdict.values())],
                      key=lambda z: z.name.lower())

##
# Hided functions
##

    async def _raw_unban(self, name, ip, unid):
        await self._send_command("removeblock", unid, ip, name)

    def _add_history(self, msg):
        if len(self._history) == 2900:
            rest = self._history.popleft()
            rest.detach()
        self._history.append(msg)

    def _get_user_list(self, unique=1, memory=0, anons=False):
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

    async def _raw_ban(self, msgid, ip, name):
        """
        Ban user with received data
        @param msgid: Message id
        @param ip: user IP
        @param name: chatango user name
        @return: bool
        """
        await self._send_command("block", msgid, ip, name)

    async def _reload(self):
        if self._usercount <= 1000:
            await self._send_command("g_participants:start")
        else:
            await self._send_command("gparticipants:start")
        await self._send_command("getpremium", "l")
        await self._send_command('getannouncement')
        await self._send_command("getbannedwords")
        await self._send_command("getratelimit")
        await self.request_banlist()
        await self.request_unbanlist()
        if self.user.ispremium:
            await self._style_init(self._user)

    async def _style_init(self, user):
        if not user.isanon:
            await user.get_profile()
        else:
            self.set_font(
                name_color="000000",
                font_color="000000",
                font_size=11,
                font_face=1)
                
    async def _disconnect(self):
        self._connected = False
        for x in self.userlist:
            x.removeSessionId(self, 0)
        await self.client._call_event("disconnect", self)

    async def _login(self, u=None, p=None):
        try:
            self._connection = await self.client.aiohttp_session.ws_connect(
                f"ws://{self.server}:8080/", origin="http://st.chatango.com")
            await self._send_command("bauth", self.name, self._uid, u or "", p or "")
        except aiohttp.client_exceptions.ClientConnectorError:
            self._connection = object()
            self._connection.closed = True
            if int(self.client.debug) > 0:
                print(f"[debug] Server {self.server} is down!")

    async def enable_bg(self):
        await self.set_bg_mode(1)

    async def disable_bg(self):
        await self.set_bg_mode(0)


    def set_font(self, name_color=None, font_color=None, font_size=None, font_face=None):
        if name_color:
            self._user._styles._name_color = str(name_color)
        if font_color:
            self._user._styles._font_color = str(font_color)
        if font_size:
            self._user._styles._font_size = int(font_size)
        if font_face:
            self._user._styles._font_face = int(font_face)

    def get_session_list(self, mode=0, memory=0):  # TODO
        if mode < 2:
            return [(x.name if mode else x, len(x.getSessionIds(self))) for x in
                    self._get_user_list(1, memory)]
        else:
            return [(x.showname, len(x.getSessionIds(self))) for x in
                    self._get_user_list(1, memory)]

    def get_level(self, user):
        if isinstance(user, str):
            user = User(user.strip())
        if user.name == str(self.owner.name).strip():
            return 3
        if user in self._mods:
            if self._mods.get(user).isadmin:
                return 2
            else:
                return 1
        return 0

    def ban_record(self, user):
        if isinstance(user, User):  # TODO
            user = user.name
        if user.lower() in [x.name for x in self._banlist]:
            return self._banlist[User(user)]
        return None

    async def upload_image(self, path, return_url=False):
        if self.user.isanon:
            return None
        with open(path, mode='rb') as f:
            files = {'filedata': {'filename': path,
                                  'content': f.read().decode('latin-1')}}
        account, success = _account_selector(self), None
        data, headers = multipart(dict(u=account[0], p=account[1]), files)
        headers.update(
            {"host": "chatango.com", "origin": "http://st.chatango.com"})
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post("http://chatango.com/uploadimg", data=data.encode("latin-1")) as resp:
                response = await resp.text()
                if "success" in response:
                    success = response.split(":", 1)[1]
        if success != None:
            if return_url:
                url = "http://ust.chatango.com/um/{}/{}/{}/img/t_{}.jpg"
                return url.format(self.user.name[0], self.user.name[1], self.user.name, success)
            else:
                return f"img{success}"
        return None

    def get_last_message(self, user=None):
        """Obtener el último mensaje de un usuario en una sala"""
        if not user:
            return self._history and self._history[-1] or None
        if isinstance(user, User):
            user = user.name
        for x in reversed(self.history):
            if x.user.name == user:
                return x
        return None

    async def unban_user(self, user):
        rec = self.ban_record(user)
        print("rec", rec)
        if rec:
            await self._raw_unban(rec.target.name, rec.ip, rec.unid)
            return True
        else:
            return False

    async def ban_message(self, msg: Message) -> bool:
        if self.get_level(self.user) > 0:
            name = '' if msg.user.isanon else msg.user.name
            await self._raw_ban(msg.unid, msg.ip, name)
            return True
        return False


    async def ban_user(self, user: str) -> bool:
        """
        Banear un usuario (si se tiene el privilegio)
        @param user: El usuario, str o User
        @return: Bool indicando si se envió el comando
        """
        msg = self.get_last_message(user)
        if msg and msg.user not in self.banlist:
            return await self.ban_message(msg)
        return False

    async def clear_all(self):
        """Borra todos los mensajes"""
        if self.get_level(self.user.name) > 1: # admin, or owner 
            if self.owner.name == self.user.name or ModeratorFlags.EDIT_GROUP in self._mods[self.user]:
                await self._send_command("clearall")
                return True
        return False

    async def clear_user(self, user):
        # TODO
        if self.get_level(self.user) > 0: # mod
            msg = self.get_last_message(user)
            if msg:
                name = '' if msg.user.isanon else msg.user.name
                await self._send_command("delallmsg", msg.unid, msg.ip, name)
                return True
        return False

    async def delete_message(self, message):
        if self.get_level(self.user) > 0 and message.id: # mod
            await self._send_command("delmsg", message.id)
            return True
        return False

    async def delete_user(self, user):
        if self.get_level(self.user) > 0:
            msg = self.get_last_message(user)
            if msg:
                await self.delete_message(msg)
                return True
        return False

    async def request_unbanlist(self):
        await self._send_command('blocklist', 'unblock',
                                 str(int(time.time() + self._correctiontime)), 'next',
                                 '500', 'anons', '1')

    async def request_banlist(self):  # TODO revisar
        await self._send_command('blocklist', 'block',
                                 str(int(time.time() + self._correctiontime)), 'next',
                                 '500', 'anons', '1')

    async def set_banned_words(self, part='', whole=''):
        """
        Actualiza las palabras baneadas para que coincidan con las recibidas
        @param part: Las partes de palabras que serán baneadas (separadas por
        coma, 4 carácteres o más)
        @param whole: Las palabras completas que serán baneadas, (separadas
        por coma, cualquier tamaño)
        """
        if self.user in self._mods and ModeratorFlags.EDIT_BW in self._mods[self.user]:
            await self._send_command('setbannedwords', urlreq.quote(part),
                                     urlreq.quote(whole))
            return True
        return False

    async def set_bg_mode(self, mode):
        self._bgmode = mode
        if self.connected:
            await self._send_command("getpremium", "l")
            if self.user.ispremium:
                await self._send_command('msgbg', str(self._bgmode))


    async def login(self, user_name: typing.Optional[str] = None, password: typing.Optional[str] = None):
        if self.client._using_accounts != None and not password:
            for acc in self.client.accounts:
                if acc[1].lower() == user_name.lower():
                    user_name = self.client._using_accounts[acc[0]][0]
                    password = self.client._using_accounts[acc[0]][1]
                    break
        self._user = User(user_name, isanon=False if password == "" else True)
        await self._send_command("blogin", user_name or "", password or "")

    async def logout(self):
        await self._send_command("blogout")

    async def send_message(self, message, use_html=False, flags=None):
        if not self.silent:
            message_flags = flags if flags else str(
                self.message_flags+self.badge) or str(0+self.badge)
            msg = str(message)
            if not use_html:
                msg = html.escape(msg, quote=False)
            else:
                msg = html.unescape(msg)
            _msg = msg.replace('\n', '\r').replace('~', '&#126;')
            for _message in message_cut(str(_msg), self._maxlen, self,
                                           use_html):
                await self._send_command("bm", _id_gen(), message_flags, _message)

##
# Handler events
##

    async def _rcmd_ok(self, args):  # TODO
        self._connected = True
        self._owner = User(args[0])
        self._puid = args[1]
        self._login_as = args[2]
        self._currentname = args[3]
        self._connectiontime = args[4]
        self._correctiontime = int(float(self._connectiontime) - time.time())
        self._currentIP = args[5]
        self._flags = RoomFlags(int(args[7]))
        if self._login_as == 'C':
            uname = get_anon_name(str(self._correctiontime).split(".")[
                                  0][-4:].replace('-', ''), self._puid)
            self._user = User(uname, isanon=True, ip=self._currentIP)
        elif self._login_as == 'M':
            self._user = User(self._currentname,
                              puid=self._puid, ip=self._currentIP)
        elif self._login_as == 'N':
            pass
        for mod in args[6].split(";"):
            if len(mod.split(",")) > 1:
                mod, power = mod.split(",")
                self._mods[User(mod)] = ModeratorFlags(int(power))
                self._mods[User(mod)].isadmin = ModeratorFlags(int(
                    power)) & AdminFlags != 0
        await self.client._call_event("connect", self)

    async def _rcmd_annc(self, args):
        self._announcement[0] = int(args[0])
        anc = ':'.join(args[2:])
        if anc != self._announcement[2]:
            self._announcement[2] = anc
            await self.client._call_event('AnnouncementUpdate', args[0] != '0')
        await self.client._call_event('Announcement', anc)

    async def _rcmd_pwdok(self, args):
        self._user._isanon = False
        await self._send_command("getpremium", "l")
        await self._style_init(self._user)

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
        msg = await _process(self, args)
        msg.attach(self, msg._id)
        self._add_history(msg)

    async def _rcmd_b(self, args):  # TODO
        msg = await _process(self, args)
        if self._del_dict:
            for message_inwait in self._del_dict:
                if self._del_dict[message_inwait]["m"] == msg.body and self.user == msg.user:
                    self._del_dict[message_inwait].update({"i": msg})
        self._mqueue[msg._id] = msg

    async def _rcmd_premium(self, args):  # TODO
        if self._bgmode and (args[0] == '210' or (
                isinstance(self, Room) and self._owner == self.user)):
            self.user._ispremium = True
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
            self._add_history(msg)
            await self.client._call_event("message", msg)

    async def _rcmd_gparticipants(self, args):
        """old command, chatango keep sending it."""
        await self._rcmd_g_participants(len(args) > 1 and args[1:] or '')

    async def _rcmd_g_participants(self, args):
        self._userdict = dict()
        args = ':'.join(args).split(";")  # return if not args
        for data in args:
            data = data.split(':')  # Lista de un solo usuario
            ssid = data[0]
            contime = data[1]  # Hora de conexión a la sala
            puid = data[2]
            name = data[3]
            tname = data[4]
            isanon = False
            if str(name) == 'None':
                isanon = True
                if str(tname) != 'None':
                    name = tname
                else:
                    name = get_anon_name(contime, puid)
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
                name = get_anon_name(contime, puid)
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
                await self.client._call_event('anon_leave', self, user, puid)
            else:
                await self.client._call_event('leave', self, user, puid)
        elif cambio == '1' or not before:  # Join
            user.addSessionId(self, ssid)
            if not user.isanon and user not in self.userlist:
                await self.client._call_event('join', self, user, puid)
            elif user.isanon:
                await self.client._call_event('anon_join', self, user, puid)
            self._userdict[ssid] = [contime, user]
            lista = [x[1] for x in self._userhistory]
            if user in lista:
                self._userhistory.remove(
                    [x for x in self._userhistory if x[1] == user][0])
        else:  # TODO
            if before.isanon:  # Login
                if user.isanon:
                    await self.client._call_event('anon_login', self, before, user, puid)
                else:
                    await self.client._call_event('user_login', self, before, user, puid)
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
                    await self.client._call_event('user_logout', self, before, user, puid)

            self._userdict[ssid] = [contime, user]

    async def _rcmd_mods(self, args):
        pre = self._mods
        mods = self._mods = dict()
        # Load current mods
        for mod in args:
            name, powers = mod.split(',', 1)
            utmp = User.get(name)
            self._mods[utmp] = ModeratorFlags(int(powers))
            self._mods[utmp].isadmin = ModeratorFlags(int(
                powers)) & AdminFlags != 0
        tuser = User(self._currentname)
        if (self.user not in pre and self.user in mods) or (tuser not in pre and tuser in mods):
            if self.user == tuser:
                await self.client._call_event('mod_added', self.user)
            return

        for user in self.mods - set(pre.keys()):
            await self.client._call_event("mod_added", user)
        for user in set(pre.keys()) - self.mods:
            await self.client._call_event("mod_remove", user)
        for user in set(pre.keys()) & self.mods:
            privs = set(x for x in dir(mods.get(user)) if
                        not x.startswith('_') and getattr(mods.get(user),
                                                          x) != getattr(
                pre.get(user), x))
            privs = privs - {'MOD_ICON_VISIBLE', 'value'}
            if privs:
                await self.client._call_event('mods_change', user, privs)

    async def _rcmd_groupflagsupdate(self, args):
        flags = args[0]
        self._flags = self._flags = RoomFlags(int(flags))
        await self.client._call_event('flags_update')

    async def _rcmd_blocked(self, args):  # TODO
        target = args[2] and User(args[2]) or ''
        user = User(args[3])
        if not target:
            msx = [msg for msg in self._history if msg.unid == args[0]]
            target = msx and msx[0].user or User('ANON')
            await self.client._call_event('anon_ban', user, target)
        else:
            await self.client._call_event("ban", user, target)
        self._banlist[target] = self._BANDATA(args[0], args[1], target,
                                              float(args[4]), user)

    async def _rcmd_blocklist(self, args):  # TODO
        self._banlist = dict()
        sections = ":".join(args).split(";")
        for section in sections:
            params = section.split(":")
            if len(params) != 5:
                continue
            if params[2] == "":
                continue
            user = User(params[2])
            self._banlist[user] = self._BANDATA(params[0], params[1], user,
                                                float(params[3]),
                                                User(params[4]))
        await self.client._call_event("banlist_update")

    async def _rcmd_unblocked(self, args):
        """Unban event"""
        unid = args[0]
        ip = args[1]
        target = args[2].split(';')[0]
        # bnsrc = args[-3]
        ubsrc = User(args[-2])
        time = args[-1]
        self._unbanqueue.append(
            self._BANDATA(unid, ip, target, float(time), ubsrc))
        if target == '':
            msx = [msg for msg in self._history if msg.unid == unid]
            target = msx and msx[0].user or User('anon', isanon=True)
            await self.client._call_event('anon_unban', ubsrc, target)
        else:
            target = User(target)
            if target in self._banlist:
                self._banlist.pop(target)
            await self.client._call_event("unban", ubsrc, target)

    async def _rcmd_unblocklist(self, args):
        sections = ":".join(args).split(";")
        for section in sections[::-1]:
            params = section.split(":")
            if len(params) != 5:
                continue
            unid = params[0]
            ip = params[1]
            target = User(params[2] or 'Anon')
            time = float(params[3])
            src = User(params[4])
            self._unbanqueue.append(self._BANDATA(unid, ip, target, time, src))
        await self.client._call_event("unbanlist_update")

    async def _rcmd_clearall(self, args):
        await self.client._call_event("clearall", args[0])

    async def _rcmd_denied(self, args):
        await self.client._call_event("room_denied", self)

    async def _rcmd_updatemoderr(self, args):
        await self.client._call_event("mod_update_error", User(args[1]), args[0])

    async def _rcmd_proxybanned(self, args):
        await self.client._call_event("proxy_banned")

    async def _rcmd_show_tb(self, args):
        await self.client._call_event("show_tmp_ban", int(args[0]))

    async def _rcmd_miu(self, args):
        await self.client._call_event('bg_reload', User(args[0]))

    async def _rcmd_delete(self, args):
        """Borrar un mensaje de mi vista actual"""
        msg = self._msgs.get(args[0])
        if msg and msg in self._history:
            self._history.remove(msg)
            await self.client._call_event("message_delete", msg.user, msg)
            msg.detach()
        #
        if len(self._history) < 20 and not self._nomore:
            await self._send_command('get_more:20:0')

    async def _rcmd_deleteall(self, args):
        """Mensajes han sido borrados"""
        user = None  # usuario borrado
        msgs = list()  # mensajes borrados
        for msgid in args:
            msg = self._msgs.get(msgid)
            if msg and msg in self._history:
                self._history.remove(msg)
                user = msg.user
                msg.detach()
                msgs.append(msg)
        if msgs:
            await self.client._call_event('delete_user', user, msgs)

    async def _rcmd_bw(self, args):  # Palabras baneadas en el chat
        # TODO, actualizar el registro del chat
        part, whole = '', ''
        if args:
            part = urlreq.unquote(args[0])
        if len(args) > 1:
            whole = urlreq.unquote(args[1])
        if hasattr(self, '_bwqueue'):
            # self._bwqueue = [self._bwqueue.split(':', 1)[0] + ',' + args[0],
            #                  self._bwqueue.split(':', 1)[1] + ',' + args[1]]
            # TODO agregar un callEvent
            await self.set_banned_words(*self._bwqueue)
        await self.client._call_event("bannedwords_update", part, whole)

    async def _rcmd_getannc(self, args):
        # ['3', 'pythonrpg', '5', '60', '<nE20/><f x1100F="1">hola']
        # Enabled, Room, ?, Time, Message
        # TODO que significa el tercer elemento?
        if len(args) < 4 or args[0] == 'none':
            return
        self._announcement = [int(args[0]), int(args[3]), ':'.join(args[4:])]
        if hasattr(self, '_ancqueue'):
            # del self._ancqueue
            # self._announcement[0] = args[0] == '0' and 3 or 0
            # await self._send_command('updateannouncement', self._announcement[0],
            #                   ':'.join(args[3:]))
            pass

    async def _rcmd_getratelimit(self, args):
        pass  # print("GETRATELIMIT -> ", args)

    async def _rcmd_msglexceeded(self, args):
        # print(f"_rcmd_msglexceeded ->", args)
        await self.client._call_event("room_message_length_exceeded")

    async def _rcmd_show_fw(self, args):
        # print(f"{self.name}_rcmd_show_fw ->", args)
        pass  # Show flood warning

    async def _rcmd_ubw(self, args):  # TODO palabas desbaneadas ?)
        self._ubw = args
        # print(f"{self.name}_rcmd_ubw", args)

    async def _rcmd_climited(self, args):
        # print(f"{self.name}_rcmd_climited", args)
        pass  # Climited

    async def _rcmd_show_nlp(self, args):
        # print(f"{self.name}_rcmd_show_nlp", args)
        pass  # Auto moderation

    async def _rcmd_nlptb(self, args):
        # print(f"{self.name}_rcmd_nlptb", args)
        pass  # Auto moderation temporary ban

    async def _rcmd_tb(self, args):
        """Temporary ban sigue activo con el tiempo indicado"""
        # print(f"{self.name}_rcmd_tb", args)
        await self.client._call_event("flood_ban_repeat", int(args[0]))

    async def _rcmd_logoutfirst(self, args):
        # print(f"{self.name}_rcmd_logoutfirst", args)
        pass

    async def _rcmd_logoutok(self, args, Force=False):
        """Me he desconectado, ahora usaré mi nombre de anon"""
        name = get_anon_name(str(self._correctiontime).split(".")[0][-4:], self._puid
                             )
        self._user = User(name, isanon=True, ip=self._currentIP)
        # TODO fail aqui CLOSE
        await self.client._call_event('logout', self._user, '?')

    async def _rcmd_updateprofile(self, args):
        """Cuando alguien actualiza su perfil en un chat"""
        user = User.get(args[0])
        user._profile = None
        await self.client._call_event('profile_changes', user)

    async def _rcmd_reload_profile(self, args):
        user = User.get(args[0])
        user._profile = None
        await self.client._call_event('profile_reload', user)

    async def _rcmd_verificationchanged(self, args):
        """
        Event received when the bot is connected to a room, and you verify your mail.
        """
        pass 
