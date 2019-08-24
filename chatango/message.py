import html, re

class for_room(object):
    def __init__(self, room, args):#_time, user_name, temp_name, user_id, uid, msgid, ip_address, flags, delimiter, *message):
        args = args.split(":")
        self._time   = float(args[0])
        self._room = room
        self._user, self._temp_name, self._puid, self._unid, self._msgid, self._ip, self._channel = args[1:8]
        self.body = html.unescape(
            re.sub("<(.*?)>", "", args[9].replace("<br/>", "\n"))
            )
        # user class must me message.user