"""
Module for room related stuff
"""

from .utils import gen_uid
from .connection import Connection
import aiohttp
import asyncio
import sys
import typing
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
        
        self.user_count = 0
        self._history = dict()

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