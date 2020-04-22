"""
Module for pm related stuff
"""
from .utils import get_token, gen_uid
from .connection import Socket
import urllib.parse
import time, sys
import typing
import asyncio

from .user import User, Friend
from .message import _process_pm, format_videos

class PM(Socket):
    """
    Represents a PM Connection
    """
    def __init__(self, client):
        super().__init__(client)
        self.server = "c1.chatango.com"
        self.port = 443
        self._first_command = True
        self._correctiontime = 0

        #misc
        self._uid = gen_uid()
        self._user = None
        self._silent = 0
        self._maxlen = 1900
        self._status = dict()
        self._friends = list()
        self._blocked = list()

    def __dir__(self):
        return [x for x in
                set(list(self.__dict__.keys()) + list(dir(type(self)))) if
                x[0] != '_']

    def __repr__(self):
        return "<PM>"

    @property
    def name(self):
        return repr(self)

    @property
    def user(self):
        return self._user

    @property
    def blocked(self):
        """Lista de usuarios bloqueados en la sala"""
        return self._blocked

    @property
    def friends(self):
        return [x.name for x in self._friends]

    @property
    def status(self):
        return self._status

    def _Friend(self, user):
        friend = Friend(str(user))
        friend._client = self 
        return friend

    async def enable_background(self):
        await self._send_command("msgbg", "1")

    async def disable_background(self):
        await self._send_command("msgbg", "0")

    async def block(self, user):  # TODO
        """block a person"""
        if isinstance(user, User):
            user = user.name
        if user not in self._blocked:
            await self._send_command("block", user, user, "S")
            self._blocked.append(User(user))
            await self.client._call_event("pm_block", User(user))

    async def unblock(self, user):
        """Desbloquear a alguien"""
        if isinstance(user, User):
            user = user.name
        if user in self._blocked:
            await self._send_command("unblock", user)
            await self.client._call_event("pm_unblock", User(user))
            return True

    def get_friend(self, user):
        for friend in self._friends:
            if friend == user.lower():
                return friend

    async def add_friend(self, user_name):
        user = user_name
        friend = self.get_friend(user)
        if not friend:
            await self._send_command("wladd", user_name.lower())

    async def unfriend(self, user_name):
        user = user_name
        friend = self.get_friend(user)
        if friend:
            await self._send_command("wldelete", friend.name)

    async def _login(self, user_name: str, password: str):
        if self._first_command:
            terminator = "\x00"
            self._first_command = False
        else:
            terminator = "\r\n\0"
        token = await get_token(user_name, password)
        if not token:
            await self.client._call_event("login_fail", str(user_name))
        else:
            await self._send_command("tlogin", str(token), "2", self._uid, terminator=terminator)
    
    async def send_message(self, target, message: str, use_html: bool = False):
        if isinstance(target, User):
            target = target.name
        if self._silent > time.time():
            await self.client._call_event("pm_silent", message)
        else:
            if len(message) > 0:
                message = message #format_videos(self.user, message)
                nc = f"<n{self.user._nameColor}/>"
                finished = f"{nc}<m v=\"1\"><g xs0=\"0\">{message}</g></g></m>"
                print("FINISHED",finished)
                if sys.getsizeof(message) < 2900:
                    await self._send_command("msg", target.lower(), finished)

    async def _rcmd_seller_name(self, args):
        self._user = self._Friend(args[0])
        await self.client._call_event("connect", self)

    async def _rcmd_pong(self, args):
        await self.client._call_event("pong", self)

    async def _rmcd_premium(self, args):
        if args and args[0] == '210':
            await self.enable_background()

    async def _rcmd_time(self, args):
        self._connectiontime = float(args[0])
        self._correctiontime = float(self._connectiontime) - time.time()

    async def _rcmd_OK(self, args):
        self._connected = True
        if self.friends or self.blocked:
            self.friends.clear()
            self.blocked.clear()
        await self._send_command("wl") 
        await self._send_command("getblock")        
        await self._send_command("getpremium")
        await self.enable_background()

    async def _rcmd_wl(self, args):
        if self.client.debug:
            pass
        for i in range(len(args) // 4):
            name, last_on, is_on, idle = args[i * 4: i * 4 + 4]
            user = self._Friend(name)
            user._status = is_on
            await user._check_status(last_on, idle)
            self._friends.append(user)

    async def _rcmd_wlapp(self, args): # TODO
        """Alguien ha iniciado sesión en la app"""
        if args[0] in [x.name for x in self.friends]:
            user = Friend(args[0])
            last_on = float(args[1])
            user._status = "app"
            await self.client._call_event("pm_friend_app", user)

    async def _rcmd_wloffline(self, args):  # TODO
        if args[0] in [x.name for x in self.friends]:
            user = Friend(args[0])
            last_on = float(args[1])
            user._status = "offline"
            await self.client._call_event("pm_friend_offline", user)

    async def _rcmd_wlonline(self, args):  # TODO
        if args[0] in [x.name for x in self.friends]:
            user = Friend(args[0])
            last_on = float(args[1])
            user._status = "online"
            #await user._check_status(last_on, idle)
            await self.client._call_event("pm_friend_online", user)

    async def _rcmd_toofast(self, args):
        self._silent = time.time() + 12 # seconds to wait
        await self.client._call_event("pm_toofast")

    async def _rcmd_msglexceeded(self, args):
        if self.client.debug:
            print("msglexceeded", file=sys.stderr)
    
    async def _rcmd_msg(self, args):
        msg = await _process_pm(self, args)
        print('PM','msg', args)
        await self.client._call_event("message", msg)

    async def _rcmd_msgoff(self, args):
        msg = await _process_pm(self, args)
        msg._offline = True
        await self.client._call_event("message", msg)

