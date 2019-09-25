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
    def __init__(self, client):
        super().__init__(client)
        self.server = "i0.chatango.com"
        self._uid = gen_uid()
        
    async def _connect(self, user_name: str, password: str):
        token = await get_token(user_name, password)
        if not token:
            await self.client._call_event("login_fail", str(user_name))
        else:
            self._connection = await self.client.aiohttp_session.ws_connect(
                f"ws://{self.server}:8080/",
                origin="http://st.chatango.com")
            await self._send_command("tlogin", str(token), "2", self._uid)

    def __repr__(self):
        return "<PM>"
