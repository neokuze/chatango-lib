import html
import re
import string
import time
import enum

from .utils import gen_uid, get_anon_name, _clean_message, _parseFont, Styles
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
    '0': 'arial', '1': 'comic', '2': 'georgia', '3': 'handwriting', '4': 'impact',
    '5': 'palatino', '6': 'papirus', '7': 'times', '8': 'typewriter'
    }
    
class Message(object):  # base
    def __init__(self):
        self._user = None
        self._room = None
        self._styles = None
        self._channel = None
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
    def channel(self):
        return self._channel

    @property
    def room(self):
        return self._room

    @property
    def time(self):
        return self._time

    @property
    def body(self):
        return self._body

    @property
    def raw(self):
        return self._raw

    @property
    def styles(self):
        return self._styles

class PMBase(Message):
    def __init__(self):
        self._msgoff = False
        self._flags = str(0)
        
    @property
    def msgoff(self):
        return self._msgoff


class RoomBase(Message):
    def __init__(self, ):
        self._id = None
        self._puid = int()
        self._ip = str()
        self._unid = str()
        self._flags = dict()
        self._mentions = list()

    @property
    def id(self):
        return self._id

    @property
    def mentions(self):
        return self._mentions

    @property
    def puid(self):
        return self._puid

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
        if self._id is not None:
            self._room = room
            self._id = msgid
            self._room._msgs.update({id: self})

    def detach(self):
        if self._id is not None and self._id in self._room._msgs:
            self._room._msgs.pop(self._id)


async def _process(room, args):
    """Process message"""
    _time = float(args[0]) - room._correctiontime
    name, tname, puid, unid, msgid, ip, flags = args[1:8]
    body = ":".join(args[9:])
    msg = RoomBase()
    msg._room = room
    msg._time = float(_time)
    msg._puid = str(puid)
    msg._tempname = tname
    msg._id = msgid
    msg._unid = unid
    msg._ip = ip
    msg._raw = body
    body, n, f = _clean_message(body)
    strip_body = " ".join(body.split(" ")[:-1]) + " " + body.split(" ")[-1].replace("\n", "")
    msg._body = strip_body.strip()
    name_color = None
    isanon = False
    if name == "":
        isanon = True
        if not tname:
            if n in ['None']: n = None
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
    msg._user = User(name, ip=ip, isanon=isanon)
    msg._user._styles._name_color = name_color
    msg._styles = msg._user._styles
    msg._styles._font_size, msg._styles._font_color, msg._styles._font_face = _parseFont(f.strip())
    if msg._styles._font_size == None: msg._styles._font_size=11
    msg._flags = MessageFlags(int(flags))
    if MessageFlags.BG_ON in msg.flags:
        if MessageFlags.PREMIUM in msg.flags:
            msg._styles._use_background = 1
    msg._mentions = mentions(msg._body, room)
    msg._channel = channel(msg._room, msg._user)
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
    name_color = n or None
    font_size, font_color, font_face = _parseFont(f)
    msg = PMBase()
    msg._room = room
    msg._user = user
    msg._time = mtime
    msg._body = body
    msg._styles = msg._user._styles
    msg._styles._name_color = name_color
    msg._styles._font_size = font_size
    msg._styles._font_color = font_color
    msg._styles._font_face = font_face
    msg._channel = channel(msg._room, msg._user)
    return msg

def message_cut(message, lenth):
    result = []
    for o in [message[x:x + lenth] for x in range(0, len(message), lenth)]:
        result.append(o)
    return result 

def mentions(body, room):
    t = []
    for match in re.findall("(\s)?@([a-zA-Z0-9]{1,20})(\s)?", body):
        for participant in room.userlist:
            if participant.name.lower() == match[1].lower():
                if participant not in t:
                    t.append(participant)
    return t

class channel:
    def __init__(self, room, user):
        self.is_pm = True if room.name == "<PM>" else False
        self.user = user
        self.room = room

    def __dir__(self):
        return [x for x in
                set(list(self.__dict__.keys()) + list(dir(type(self)))) if
                x[0] != '_']

    async def send(self, message, use_html=False):
        messages = message_cut(message, self.room._maxlen)
        for message in messages:
            if self.is_pm:
                await self.room.client.pm.send_message(self.user.name, message, use_html=use_html)
            else:
                await self.room.send_message(message, use_html=use_html)

    async def send_pm(self, message):
        self.is_pm = True
        await self.send(message)

def format_videos(user, pmmessage): pass #TODO TESTING
#     msg = pmmessage
#     tag = 'i'
#     r = []
#     for word in msg.split(' '):
#         if msg.strip() != "":
#             regx = re.compile(r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?(?P<id>[A-Za-z0-9\-=_]{11})') #"<" + tag + "(.*?)>", msg)
#             match = regx.match(word)
#             w = "<g x{0._fontSize}s{0._fontColor}=\"{0._fontFace}\">".format(user)
#             if match:
#                 seek = match.group('id')
#                 word = f"<i s=\"vid','//yt','{seek}\" w=\"126\" h=\"93\"/>{w}"
#                 r.append(word)
#             else:
#                 if not r:
#                     r.append(w+word)
#                 else:
#                     r.append(word)
#             count = len([x for x in r if x == w])
#             print(count)

#     print(r)
#     return " ".join(r)
