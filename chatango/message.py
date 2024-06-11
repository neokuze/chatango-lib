import re
import time
import enum
from typing import Optional

from .utils import get_anon_name, _clean_message, _parseFont, public_attributes
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


Fonts = {
    "0": "arial",
    "1": "comic",
    "2": "georgia",
    "3": "handwriting",
    "4": "impact",
    "5": "palatino",
    "6": "papirus",
    "7": "times",
    "8": "typewriter",
}


class Message:
    def __init__(self):
        self.user: Optional[User] = None
        self.room = None
        self.time = 0.0
        self.body = str()
        self.raw = str()
        self.styles = None
        self.channel: Optional[Channel] = None

    def __dir__(self):
        return public_attributes(self)

    def __repr__(self):
        return f'<Message {self.room} {self.user} "{self.body}">'


class PMMessage(Message):
    def __init__(self):
        self.msgoff = False
        self.flags = str(0)


class RoomMessage(Message):
    def __init__(self):
        self.id = None
        self.puid = str()
        self.ip = str()
        self.unid = str()
        self.flags = 0
        self.mentions = list()

    def attach(self, room, msgid):
        if self.id is not None:
            self.room = room
            self.id = msgid
            self.room._msgs.update({id: self})

    def detach(self):
        if self.id is not None and self.id in self.room._msgs:
            self.room._msgs.pop(self.id)


async def _process(room, args):
    """Process message"""
    _time = float(args[0]) - room._correctiontime
    name, tname, puid, unid, msgid, ip, flags = args[1:8]
    body = ":".join(args[9:])
    msg = RoomMessage()
    msg.room = room
    msg.time = float(_time)
    msg.puid = str(puid)
    msg.id = msgid
    msg.unid = unid
    msg.ip = ip
    msg.raw = body
    body, n, f = _clean_message(body)
    strip_body = (
        " ".join(body.split(" ")[:-1]) + " " + body.split(" ")[-1].replace("\n", "")
    )
    msg.body = strip_body.strip()
    name_color = None
    isanon = False
    if name == "":
        isanon = True
        if not tname:
            if n in ["None"]:
                n = None
            if not isinstance(n, type(None)):
                name = get_anon_name(n, puid)
            else:
                name = get_anon_name("", puid)
        else:
            name = tname
    else:
        if n:
            name_color = n
        else:
            name_color = None
    msg.user = User(name, ip=ip, isanon=isanon)
    msg.user._styles._name_color = name_color
    msg.styles = msg.user._styles
    msg.styles._font_size, msg.styles._font_color, msg.styles._font_face = _parseFont(
        f.strip()
    )
    if msg.styles._font_size == None:
        msg.styles._font_size = 11
    msg.flags = MessageFlags(int(flags))
    if MessageFlags.BG_ON in msg.flags:
        if MessageFlags.PREMIUM in msg.flags:
            msg.styles._use_background = 1
    msg.mentions = mentions(msg.body, room)
    msg.channel = Channel(msg.room, msg.user)
    ispremium = MessageFlags.PREMIUM in msg.flags
    if msg.user.ispremium != ispremium:
        evt = (
            msg.user._ispremium != None
            and ispremium != None
            and _time > time.time() - 5
        )
        msg.user._ispremium = ispremium
        if evt:
            await room.handler._call_event("premium_change", msg.user, ispremium)
    return msg


async def _process_pm(room, args):
    name = args[0] or args[1]
    if not name:
        name = args[2]
    user = User(name)
    mtime = float(args[3]) - room._correctiontime
    rawmsg = ":".join(args[5:])
    body, n, f = _clean_message(format_videos(user.styles, rawmsg), pm=True)
    name_color = n or None
    font_size, font_color, font_face = _parseFont(f)
    msg = PMMessage()
    msg.room = room
    msg.user = user
    msg.time = mtime
    msg.body = body
    msg.raw = rawmsg
    msg.styles = msg.user._styles
    msg.styles._name_color = name_color
    msg.styles._font_size = font_size
    msg.styles._font_color = font_color
    msg.styles._font_face = font_face
    msg.channel = Channel(msg.room, msg.user)
    return msg


def message_cut(message, lenth):
    result = []
    for o in [message[x : x + lenth] for x in range(0, len(message), lenth)]:
        result.append(o)
    return result


def mentions(body, room):
    t = []
    for match in re.findall(r"([ \t\n\r\f\v])?@([a-zA-Z0-9]{1,20})([ \t\n\r\f\v])?", body):
        for participant in room.userlist:
            if participant.name.lower() == match[1].lower():
                if participant not in t:
                    t.append(participant)
    return t


class Channel:
    def __init__(self, room, user):
        self.is_pm = True if room.name == "<PM>" else False
        self.user = user
        self.room = room

    def __dir__(self):
        return public_attributes(self)

    async def send_message(self, message, use_html=False):
        messages = message_cut(message, self.room._maxlen)
        for message in messages:
            if self.is_pm:
                await self.room.send_message(self.user.name, message, use_html=use_html)
            else:
                await self.room.send_message(message, use_html=use_html)

    async def send_pm(self, message):
        self.is_pm = True
        await self.send_message(message)


def format_videos(user: User, msg: str) -> str:
    pattern = r'<i s="vid://yt:([A-Za-z0-9_-]{11})"[^>]*?>'

    def replace_match(match):
        video_id = match.group(1)
        url = f" https://www.youtube.com/watch?v={video_id}"
        return url

    formatted_msg = re.sub(pattern, replace_match, msg)
    #w = f"<g x{user.styles._font_size}s{user.styles._font_color}=\"{user.styles._font_face}\">"
    return formatted_msg
