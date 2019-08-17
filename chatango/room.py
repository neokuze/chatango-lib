import aiohttp
import asyncio
specials = {'mitvcanal': 56, 'animeultimacom': 34, 'cricket365live': 21, 'pokemonepisodeorg': 22, 'animelinkz': 20, 'sport24lt': 56, 'narutowire': 10, 'watchanimeonn': 22, 'cricvid-hitcric-': 51, 'narutochatt': 70, 'leeplarp': 27, 'stream2watch3': 56,
            'ttvsports': 56, 'ver-anime': 8, 'vipstand': 21, 'eafangames': 56, 'soccerjumbo': 21, 'myfoxdfw': 67, 'kiiiikiii': 21, 'de-livechat': 5, 'rgsmotrisport': 51, 'dbzepisodeorg': 10, 'watch-dragonball': 8, 'peliculas-flv': 69, 'tvanimefreak': 54, 'tvtvanimefreak': 54}
tsweights = [['5', 75], ['6', 75], ['7', 75], ['8', 75], ['16', 75], ['17', 75], ['18', 75], ['9', 95], ['11', 95], ['12', 95], ['13', 95], ['14', 95], ['15', 95], ['19', 110], ['23', 110], ['24', 110], ['25', 110], ['26', 110], ['28', 104], ['29', 104], ['30', 104], ['31', 104], ['32', 104], ['33', 104], ['35', 101], ['36', 101], ['37', 101], ['38', 101], ['39', 101], ['40', 101], ['41', 101], ['42', 101], ['43', 101], ['44', 101], [
    '45', 101], ['46', 101], ['47', 101], ['48', 101], ['49', 101], ['50', 101], ['52', 110], ['53', 110], ['55', 110], ['57', 110], ['58', 110], ['59', 110], ['60', 110], ['61', 110], ['62', 110], ['63', 110], ['64', 110], ['65', 110], ['66', 110], ['68', 95], ['71', 116], ['72', 116], ['73', 116], ['74', 116], ['75', 116], ['76', 116], ['77', 116], ['78', 116], ['79', 116], ['80', 116], ['81', 116], ['82', 116], ['83', 116], ['84', 116]]


def getServer(group):
    """
    Get the server host for a certain room.

    @type group: str
    @param group: room name

    @rtype: str
    @return: the server's hostname
    """
    try:
        sn = specials[group]
    except KeyError:
        group = group.replace("_", "q")
        group = group.replace("-", "q")
        fnv = int(group[0:5], 36)
        lnv = group[6:9]
        if lnv:
            lnv = int(lnv, 36)
            lnv = max(lnv, 1000)
        else:
            lnv = 1000
        num = (fnv % lnv) / lnv
        maxnum = sum(x[1] for x in tsweights)
        cumfreq = 0
        sn = 0
        for wgt in tsweights:
            cumfreq += wgt[1] / maxnum
            if num <= cumfreq:
                sn = int(wgt[0])
                break
    return f"s{sn}.chatango.com"


class Room:
    def __new__(cls, client, name: str):
        name = name.lower()
        if name not in client._rooms:
            self = super(Room, cls).__new__(cls)
            client._rooms[name] = self
        return client._rooms[name]

    def __init__(self, client, name: str):
        if name in client._rooms:
            return
        self.name = name
        self.client = client
        self.server = getServer(name)
        self._recv_task = None
        self._connection = None

    async def _do_recv(self):
        while True:
            message = await self._connection.receive()
            assert message.type is aiohttp.WSMsgType.TEXT
            
    async def connect(self, name=None, password=None):
        assert not self.connected
        self._connection = await self.client.aiohttp_session.ws_connect(f"ws://{self.server}:8080/")
        self._recv_task = asyncio.create_task(self._do_recv())

    async def disconnect(self):
        assert self.connected
        await self._connection.disconnect()
        self._recv_task.cancel()
        try:
            await self._recv_task
        except asyncio.CancelledError:
            pass
        self._recv_task = None
        self._connection = None

    @property
    def connected(self):
        return self._recv_task is not None
