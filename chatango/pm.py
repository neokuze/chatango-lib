"""
Module for pm related stuff
"""

class PM:
    def __init__(self, client):
        self.client = client
        self.user = None

    async def connect(self, user_name=None, password=None):
        raise NotImplementedError

    async def disconnect(self):
        raise NotImplementedError

    @property
    def connected(self):
        raise NotImplementedError

    