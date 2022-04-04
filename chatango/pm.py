"""
Module for pm related stuff
"""
from .utils import get_token, gen_uid
from .connection import Connection
import urllib.parse
import time
import sys
import typing
import asyncio

from .user import User, Friend
from .message import _process_pm, message_cut


# TODO Unhandled received command kickingoff

class PM(Connection):
    """
    Represents a PM Connection
    """

    def __init__(self, client):
        super().__init__(client, ws=False)
        self.server = "c1.chatango.com"
        self.port = 443
        self.__token = None
        self._first_command = True
        self._correctiontime = 0
        self.__online = None

        # misc
        self._uid = gen_uid()
        self._user = None
        self._silent = 0
        self._maxlen = 11600
        self._friends = dict()
        self._blocked = list()
        self._premium = False
        self._history = list()

    def __dir__(self):
        return [x for x in
                set(list(self.__dict__.keys()) + list(dir(type(self)))) if
                x[0] != '_']

    def __repr__(self):
        return "<PM>"

    @property
    def im_online(self):
        return self.__online

    @property
    def name(self):
        return repr(self)

    @property
    def is_pm(self):
        return True

    @property
    def user(self):
        return self._user

    @property
    def premium(self):
        return self._premium

    @property
    def history(self):
        return self._history

    @property
    def blocked(self):
        """Lista de usuarios bloqueados en la sala"""
        return self._blocked

    @property
    def friends(self):
        return list(self._friends.keys())

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
        if isinstance(user, User):
            user = user.name
        if user.lower() in self.friends:
            return self._friends[user]
        else:
            user = User(user)
            self._friends[user] = Friend(user, self)
            return self._friends[user]

    def _add_to_history(self, args):
        if len(self.history) >= 10000:
            self._history = self._history[1:]
        self._history.append(args)

    async def addfriend(self, user_name):
        if user_name not in self.friends:
            await self._send_command("wladd", user_name.lower())
            await self._send_command("track", user_name.lower())
            return True
        return False

    async def unfriend(self, user_name):
        user = user_name
        friend = self.get_friend(user)
        if friend:
            await self._send_command("wldelete", friend.name)
            return True
        return False

    async def _login(self, user_name=str, password=str):
        if self.client._using_accounts:
            user_name, password = self.client._using_accounts[0]
        self.__token = await get_token(user_name, password)
        if self.__token:
            self.__online = True
            await self._send_command("tlogin", self.__token, "2", self._uid)

    async def send_message(self, target, message: str, use_html: bool = False):
        if isinstance(target, User):
            target = target.name
        if self._silent > time.time(): # manual rate limit
            await self.client._call_event("pm_silent", message)
        else:
            if len(message) > 0:
                for msg in message_cut(message, self._maxlen, self, use_html):
                    await self._send_command("msg", target.lower(), msg)

    async def _rcmd_seller_name(self, args):
        self._user = User(args[0])
        await self.client._call_event("connect", self)

    async def _rcmd_pong(self, args):
        await self.client._call_event("pong", self)

    async def _rcmd_premium(self, args):
        if args and args[0] == '210':
            self._premium = True
        else:
            self._premium = False
        if self.premium:
            await self.enable_background()

    async def _rcmd_time(self, args):
        self._connectiontime = float(args[0])
        self._correctiontime = float(self._connectiontime) - time.time()

    async def _rcmd_DENIED(self, args):
        await self.client._call_event("pm_denied", self, args)

    async def _rcmd_OK(self, args):
        self._connected = True
        if self.friends or self.blocked:
            self.friends.clear()
            self.blocked.clear()
        await self._send_command("getpremium")
        await self._send_command("wl")
        await self._send_command("getblock")

    async def _rcmd_toofast(self, args):
        self._silent = time.time() + 12  # seconds to wait
        await self.client._call_event("pm_toofast")

    async def _rcmd_msglexceeded(self, args):
        if self.client.debug:
            print("msglexceeded", file=sys.stderr)

    async def _rcmd_msg(self, args):
        msg = await _process_pm(self, args)
        if self.client.debug > 2:
            print("pmmsg:", args)
        self._add_to_history(msg)
        await self.client._call_event("message", msg)

    async def _rcmd_msgoff(self, args):
        msg = await _process_pm(self, args)
        msg._offline = True
        self._add_to_history(msg)

    async def _rcmd_wlapp(self, args): pass

    async def _rcmd_wloffline(self, args): pass

    async def _rcmd_wlonline(self, args): pass

    async def _rcmd_wl(self, args):
        """Lista de contactos recibida al conectarse"""
        # Restart contact list
        self._friends.clear()
        # Iterate over each contact
        for i in range(len(args) // 4):
            name, last_on, is_on, idle = args[i * 4: i * 4 + 4]
            user = User(name)
            friend = Friend(user, self)
            if last_on == "None":
                last_on = 0
            if is_on in ["off", "offline"]:
                friend._status = "offline"
            elif is_on in ["on", "online"]:
                friend._status = "online"
            elif is_on in ["app"]:
                friend._status = "app"
            friend._check_status(float(last_on), None, int(idle))
            self._friends[str(user.name)] = friend
            await self._send_command("track", user.name)

    async def _rcmd_track(self, args):
        friend = self.get_friend(args[0])
        friend._idle = False
        if args[2] == "online":
            friend._last_active = time.time() - (int(args[1]) * 60)
        elif args[2] == "offline":
            friend._last_active = float(args[1])
        if args[1] in ["0"] and args[2] in ["app"]:
            friend._status = "app"
        else:
            friend._status = args[2]

    async def _rcmd_kickingoff(self, args):
        self.__online = False

    async def _rcmd_idleupdate(self, args):
        friend = self.get_friend(args[0])
        friend._last_active = time.time()
        friend._idle = True if args[1] == '0' else False

    async def _rcmd_status(self, args):
        friend = self.get_friend(args[0])
        status = True if args[2] == "online" else False
        friend._check_status(float(args[1]), status, 0)
        await self.client._call_event(f"pm_contact_{args[2]}", friend)

    async def _rcmd_block_list(self, args):
        if self.client.debug > 1:
            print("block_list_pm:", args)

    async def _rcmd_wladd(self, args):
        if args[1] == "invalid":
            return
        user = args[0]

        if user not in self.friends:
            friend = Friend(User(user), self)
            self._friends[user] = friend
            await self.client._call_event("pm_contact_addfriend", friend)
            await self._send_command("wladd", friend.user.name)

    async def _rcmd_wldelete(self, args):
        if args[1] == "deleted":
            friend = args[0]
            if friend in self._friends:
                del self._friends[friend]
                await self.client._call_event("pm_contact_unfriend", args[0])


"""
RE-MAKE
"""
