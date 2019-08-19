"""
Module for pm related stuff
"""
from .connection import Connection
import urllib.parse
import aiohttp
import typing


class PM(Connection):
    """
    Represents a PM Connection
    """

    # async def _get_auth(self, user_name: str, password: str) -> typing.Optional[str]:
    #     session: aiohttp.ClientSession
    #     session = self.client.aiohttp_session
    #     data = urllib.parse.urlencode({
    #         "user_id": user_name,
    #         "password": password,
    #         "storecookie": "on",
    #         "checkerrors": "yes"
    #     }).encode()
    #     async with session.post("http://chatango.com/login", data=data) as response:
    #         print(response.cookies)

    async def _connect(self, user_name: str, password: str):
        # ch.py uses it but i guess it isn't necesary?
        # auid = self._get_auth(user_name, password)
        self._connection = await self.client.aiohttp_session.ws_connect(
            "ws://i0.chatango.com:8080/",
            origin="http://st.chatango.com"
        )
        await self._send_command("blogin", user_name, password)

    def __repr__(self):
        return "<PM>"
