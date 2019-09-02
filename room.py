"""
Module for room related stuff
"""

from .utils import gen_uid, has_flag
from .connection import Connection
from .message import Message, MESSAGE_FLAGS
import aiohttp
import asyncio
import sys
import typing
import html, re
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

ROOM_FLAGS = {
    "list_taxonomy":                1, "noanons":              4, "noflagging":          8,
    "nocounter":                   16, "noimages":            32, "nolinks":            64,
    "novideos":                   128, "nostyledtext":       256, "nolinkschatango":   512,
    "nobrdcastmsgwithbw":        1024, "ratelimitregimeon": 2048, "channelsdisabled": 8192,
    "nlp_singlemsg":            16384, "nlp_msgqueue":     32768, "broadcast_mode":  65536,
    "closed_if_no_mods":       131072, "is_closed":       262144, "show_mod_icons": 524288,
    "mods_choose_visibility": 1048576, "nlp_ngram":      2097152, "no_proxies":    4194304,
    "has_xml":              268435456, "unsafe":       536870912
    }

MODERATOR_FLAGS = {
    "deleted":           1, "edit_mods":                 2, "edit_mod_visibility":   4,
    "edit_bw":           8, "edit_restrictions":        16, "edit_group":           32,
    "see_counter":      64, "see_mod_channel":         128, "see_mod_actions":     256,
    "edit_nlp":        512, "edit_gp_annc":           1024, "edit_admins":        2048,
    "edit_supermods": 4096, "no_sending_limitations": 8192, "see_ips":           16384,
    "close_group":   32768, "can_broadcast":         65536, "mod_icon_visible": 131072,
    "is_staff":     262144, "staff_icon_visible":   524288
    }

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
        self._unid = str()
        self._mqueue = dict()
        self._msgs = dict()
        self._usercount = 0
        self._history = dict()
        self._maxlen = 2900

    def _addHistory(self, msg):
        pass

    async def _connect(self, user_name: typing.Optional[str] = None, password: typing.Optional[str] = None):
        self._user = user_name
        self._connection = await self.client.aiohttp_session.ws_connect(
            f"ws://{self.server}:8080/",
            origin="http://st.chatango.com"
        )
        await self._send_command("bauth", self.name, self._uid, user_name or "", password or "")
    
    def __repr__(self):
        return f"<Room {self.name}, {f'connected as {self._user}' if self.connected else 'not connected'}>"

    async def send_message(self, message):
        if len(message) > 0:
        	e = "000000"
        	name_color = "<n" + e + "/>"
        	font_size = 11
        	font_face = 1
        	font_color = "000000"
        	message = name_color + "<f x{}{}=\"{}\">".format(str(font_size), font_color,font_face) + "\r".join(message) + "</f>"
        	await self._send_command("bm", "chlb", message)

    async def _rcmd_ok(self, args):
        args = args.split(":")
        self.owner = args[0]
        self._unid = args[1]
        self._user = args[3]

    async def _rcmd_inited(self, args):
        pass
    async def _rcmd_pong(self, args):
        await self.client._call_event("pong")
    async def _rcmd_n(self, user_count):
        self.user_count = int(user_count, 16)
    async def _rcmd_i(self, args):
        await self._rcmd_b(args)
    async def _rcmd_b(self, args):
        args = args.split(":")
        _time = float(args[0])
        name, tname, puid, unid, msgid, ip, flags = args[1:8]
        body = args[9]
        msg = Message()
        msg._room = self
        msg._time = float(_time)
        msg._user = name or tname
        msg._puid = int(puid)
        msg._tempname = tname
        msg._msgid = str(msgid)
        msg._unid = str(unid)
        msg._ip = str(ip)
        msg._body = html.unescape(
            re.sub("<(.*?)>", "", body.replace("<br/>", "\n"))
            )
        for key, value in MESSAGE_FLAGS.items():
            if has_flag(flags, value):
                msg._flags[key] = True
            else:
                msg._flags[key] = False
        self._mqueue[msg._msgid] = msg
    async def _rcmd_u(self, arg):
        args = arg.split(":")
        if args[0] in self._mqueue:
            msg = self._mqueue.pop(args[0])
            if msg._user != self._user:
                pass
            msg.attach(self, args[1])
            await self.client._call_event("message", msg)