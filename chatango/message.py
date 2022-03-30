import html
import re
import string
import time
import enum

from .utils import gen_uid, get_anon_name, _clean_message, _parseFont, _fontFormat, _videoImagePMFormat, Styles
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
    rawmsg = ":".join(args[9:])
    msg = RoomBase()
    msg._room = room
    msg._time = float(_time)
    msg._puid = str(puid)
    msg._tempname = tname
    msg._id = msgid
    msg._unid = unid
    msg._ip = ip
    msg._raw = rawmsg
    body, n, f = _clean_message(rawmsg)
    if body[::-1][:1] == "\n":
        body = body[:-1]
    msg._body = body
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
    msg._styles._font_size, msg._styles._font_color, msg._styles._font_face = _parseFont(f)
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
    font_size, font_color, font_face = _parseFont(f, pm=True)
    msg = PMBase()
    msg._room = room
    msg._user = user
    msg._time = mtime
    msg._body = body
    msg._rawmsg = rawmsg
    msg._styles = msg._user._styles
    msg._styles._name_color = name_color
    msg._styles._font_size = font_size
    msg._styles._font_color = font_color
    msg._styles._font_face = font_face
    msg._channel = channel(msg._room, msg._user)
    return msg

def message_cut(msg: str, lenth, room, _html: False):
    # TODO ajustar envío de texto con tabulaciones
    if len(msg) + msg.count(' ') * 5 > lenth:
        if room._BigMessageCut:
            msg = msg[:lenth]
        else:
            # partir el mensaje en pedacitos y formatearlos por separado
            espacios = msg.count(' ') + msg.count('\t')
            particion = lenth
            conteo = 0
            while espacios * 6 + particion > lenth:
                particion = len(
                    msg[:particion - espacios])  # Recorrido máximo 5
                espacios = msg[:particion].count(' ') + msg[
                                                        :particion].count(
                    '\t')
                conteo += 1
            return message_cut(msg[:particion], lenth, room,
                                        _html) + message_cut(
                msg[particion:], lenth, room,
                                        _html)
    fc = room.user.styles.font_color.lower()
    nc = room.user.styles.name_color
    if not _html:
        msg = html.escape(msg, quote=False)

    msg = msg.replace('\n', '\r').replace('~', '&#126;')
    for x in set(re.findall('<[biu]>|</[biu]>', msg)):
        msg = msg.replace(x, x.upper()).replace(x, x.upper())
    if room.name == '<PM>':
        formt = '<n{}/><m v="1"><g x{:0>2.2}s{}="{}">{}</g></m>'
        fc = '{:X}{:X}{:X}'.format(*tuple(
            round(int(fc[i:i + 2], 16) / 17) for i in
            (0, 2, 4))).lower() if len(fc) == 6 else fc[:3].lower()
        msg = msg.replace('&nbsp;', ' ')  # fix
        msg = _videoImagePMFormat(msg)
        if not _html:
            msg = _fontFormat(msg)
        msg = convertPM(msg)  # TODO No ha sido completamente probado
    else:  # Room
        if not _html:
            # Reemplazar espacios múltiples
            # TODO mejorar sin alterar enlaces
            msg = msg.replace('\t', ' %s ' % ('&nbsp;' * 2))
            msg = msg.replace('   ', ' %s ''' % ('&nbsp;'))
            msg = msg.replace('&nbsp;  ', '&nbsp;&nbsp; ')
            msg = msg.replace('&nbsp;  ', '&nbsp;&nbsp; ')
            msg = msg.replace('  ', ' &#8203; ')
        formt = '<n{}/><f x{:0>2.2}{}="{}">{}'
        if not _html:
            msg = _fontFormat(msg)
        if room.user.isanon:
            # El color del nombre es el tiempo de conexión y no hay fuente
            nc = str(room._connectiontime).split('.')[0][-4:]
            formt = '<n{0}/>{4}'

    if type(msg) != list:
        msg = [msg]
    return [
        formt.format(nc, str(room.user.styles.font_size), fc, room.user.styles.font_face,
                        unimsg) for unimsg in msg]

def convertPM(msg: str) -> str:
    """
    Convertir las fuentes de un mensaje normal en fuentes para el PM
    Util para usar múltiples fuentes
    @param msg: Mensaje con fuentes incrustadas
    @return: Mensaje con etiquetas f convertidas a g
    """
    pattern = re.compile(r'<f x(\d{1,2})?([a-fA-F0-9]{6}|[a-fA-F0-9]{3})=(.*?)>')

    def repl(match):
        s, c, f = match.groups()
        if s is None:
            s = 11
        else:
            s = int(s)
        if len(c) == 6:
            c = '{:X}{:X}{:X}'.format(
                round(int(c[0:2], 16) / 17),  # r
                round(int(c[2:4], 16) / 17),  # g
                round(int(c[4:6], 16) / 17)  # b
            )
        return '</g><g x{:02}s{}="{}">'.format(s, c, f[1:-1])

    return pattern.sub(repl, msg)

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
        if self.is_pm:
            await self.room.client.pm.send_message(self.user.name, message, use_html=use_html)
        else:
            await self.room.send_message(message, use_html=use_html)

    async def send_pm(self, message):
        self.is_pm = True
        await self.send(message)
