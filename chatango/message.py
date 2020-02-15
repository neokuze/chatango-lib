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


class Message(object):  # base
    def __init__(self):
        self._user = None
        self._room = None
        self._nameColor = str("000000")
        self._fontColor = str("000000")
        self._fontSize = 12
        self._fontFace = 0
        self._time = 0
        self._body = str()
        self._raw = str()

    def __dir__(self):
        return [x for x in
                set(list(self.__dict__.keys()) + list(dir(type(self)))) if
                x[0] != '_']

    def __repr__(self):
        return "<Message>"

    @property
    def user(self):
        return self._user

    @property
    def room(self):
        return self._room

    @property
    def nameColor(self):
        return self._nameColor

    @property
    def fontColor(self):
        return self._fontColor

    @property
    def fontSize(self):
        return self._fontSize

    @property
    def time(self):
        return self._time

    @property
    def body(self):
        return self._body

    @property
    def raw(self):
        return self._raw


class PMBase(Message):
    def __init__(self):
        self._msgoff = False

    @property
    def msgoff(self):
        return self._msgoff


class RoomBase(Message):
    def __init__(self, ):
        self._msgid = None
        self._puid = int()
        self._ip = str()
        self._unid = str()
        self._flags = dict()
        self._mentions = list()

    @property
    def msgid(self):
        return self._msgid

    @property
    def mentions(self):
        return self._mentions

    @property
    def unid(self):
        return self._unid

    @property
    def flags(self):
        return self._flags

    @property
    def ip(self):
        return self._ip

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
    msg = RoomBase()
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
    msg._raw = ":".join(args)
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
    msg._mentions = mentions(msg._body, room)
    ispremium = MessageFlags.PREMIUM in msg._flags
    if msg._user.ispremium != ispremium:
        evt = msg._user._ispremium != None and ispremium != None and _time > time.time() - 5
        msg._user._ispremium = ispremium
        if evt:
            await room.client._call_event("premium_change", msg._user, ispremium)
    return msg


async def _process_pm(room, args):
    name = args[0] or args[1]
    if not name:
        name = args[2]
    user = User(name)
    mtime = float(args[3]) - room._correctiontime
    rawmsg = ':'.join(args[5:])
    body, n, f = _clean_message(rawmsg, pm=True)
    nameColor = n or None
    fontSize, fontColor, fontFace = _parseFont(f)
    msg = PMBase()
    msg._room = room
    msg._user = user
    msg._time = mtime
    msg._body = body
    msg._nameColor = nameColor
    msg._fontSize = fontSize
    msg._fontColor = fontColor
    msg._fontFace = fontFace
    return msg


def mentions(body, room):
    t = []
    for match in re.findall("(\s)?@([a-zA-Z0-9]{1,20})(\s)?", body):
        for participant in room.userlist:
            if participant.name.lower() == match[1].lower():
                if participant not in t:
                    t.append(participant)
    return t
