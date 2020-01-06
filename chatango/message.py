import html
import re
import string
import time
import enum

from .utils import gen_uid, getAnonName, _clean_message, _parseFont
from .user import User

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
        self._mentions = list()
        self._raw = str()

    def __dir__(self):
        return [x for x in
                set(list(self.__dict__.keys()) + list(dir(type(self)))) if
                x[0] != '_']
    def __repr__(self):
        return f"<Message: {self._msgid}>"

    @property
    def mentions(self):
        return self._mentions
    
    @property
    def raw(self):
        return f"<User: {self._user.showname}, Message_Raw: {self._raw}"

    @property
    def user(self):
        return self._user

    @property
    def unid(self):
        return self._unid

    @property
    def body(self):
        return ' '.join(str(self._body).replace('\n', ' ').split(' '))

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

    @property
    def msgid(self):
        return self._msgid

    def attach(self, room, msgid):
        if self._msgid is not None:
            self._room = room
            self._msgid = msgid
            self._room._msgs.update({msgid: self})

    def detach(self):
        if self._msgid is not None and self._msgid in self._room._msgs:
            self._room._msgs.pop(self._msgid)

async def _process(room, args):
        """Process message"""
        _time = float(args[0]) - 0
        name, tname, puid, unid, msgid, ip, flags = args[1:8]
        body = ":".join(args[9:])
        msg = Message()
        msg._room = room
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
        msg._raw = body
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
                await room.client._call_event("premium_change", msg._user, ispremium)
        for match in re.findall("(\s)?@([a-zA-Z0-9]{1,20})(\s)?", msg._body):
            for participant in room.userlist:
                if participant.name.lower() == match[1].lower():
                    if participant not in msg._mentions:
                        msg._mentions.append(participant)
        return msg
