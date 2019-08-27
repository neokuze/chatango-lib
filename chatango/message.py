import html, re
MESSAGE_FLAGS = {
    "premium":           4, "bg_on":            8, "media_on":         16,
    "censored":         32, "show_mod_icon":   64, "show_staff_icon": 128,
    "default_icon":     64, "channel_red":    256, "channel_orange":  512,
    "channel_green":  1024, "channel_cyan":  2048, "channel_blue":   4096,
    "channel_purple": 8192, "channel_pink": 16384, "channel_mod":   32768
    }
class Message(object):
    def __init__(self):
        self._msgid = None
        self._time = 0
        self._user = None
        self._body = str()
        self._room = None
        self._ip = str()
        self._unid = str()
        self._puid = int()
        self._nameColor = str("000")
        self._fontSize = 11
        self._fontFace = 0
        self._fontColor = str("000")
        self._flags = dict()

    def attach(self, room, msgid):
        if self._msgid is not None:
            self._room = room
            self._msgid = msgid
            self._room._msgs.update({msgid: self})
            
    def detach(self):
        if self._msgid is not None and self._msgid in self._room._msgs:
            self._room._msgs.pop(self._msgid)