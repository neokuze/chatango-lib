"""
Utility module
"""
import functools
import asyncio
import random
import typing
import html
import re
import asyncio, aiohttp

async def get_token(user_name, passwd):
    payload = {
            "user_id": str(user_name).lower(),
            "password": str(passwd),
            "storecookie": "on",
            "checkerrors": "yes"
        }
    s = "auth.chatango.com"
    async with aiohttp.ClientSession() as session:
        async with session.post('http://chatango.com/login',
                        data=payload) as resp:
            _token = str(resp.cookies.get(s))
            if s+'=' in _token:
                token = _token.split(s+'=')[1].split(";")[0]
            else:
                token = False
            return token
    return False

def gen_uid() -> str:
    """
    Generate an uid
    """
    return str(random.randrange(10 ** 15, 10 ** 16))


def _clean_message(msg: str, pm: bool = False) -> [str, str, str]:  # TODO
    n = re.search("<n(.*?)/>", msg)
    tag = pm and 'g' or 'f'
    f = re.search("<" + tag + "(.*?)>", msg)
    msg = re.sub("<" + tag + ".*?>" + '|"<i s=sm://(.*)"', "", msg)

    wink = '<i s="sm://wink" w="14.52" h="14.52"/>'

    if n:
        n = n.group(1)
    if f:
        f = f.group(1)
    msg = re.sub("<n.*?/>", "", msg)
    msg = _strip_html(msg)
    msg = html.unescape(msg).replace('\r', '\n')
    return msg, n or '', f or ''


def _strip_html(msg: str) -> str:
    li = msg.split("<")
    if len(li) == 1:
        return li[0]
    else:
        ret = list()
        for data in li:
            data = data.split(">", 1)
            if len(data) == 1:
                ret.append(data[0])
            elif len(data) == 2:
                if data[0].startswith("br"):
                    ret.append("\n")
                ret.append(data[1])
        return "".join(ret)


def getAnonName(puid: str, tssid: str) -> str:
    return 'anon' + _getAnonId(puid.zfill(8)[4:8], tssid).zfill(4)


def _getAnonId(puid: str, ts: str) -> str:
    if not ts or len(ts) < 4:
        ts = '3452'
    else:
        ts = ts.split('.')[0][-4:]
    __reg5 = ''
    __reg1 = 0
    while __reg1 < len(puid):
        __reg4 = int(puid[__reg1])
        __reg3 = int(ts[__reg1])
        __reg2 = str(__reg4 + __reg3)
        __reg5 += __reg2[-1:]
        __reg1 += 1
    return __reg5


def _parseFont(f: str, pm=False) -> (str, str, str):
    if pm:
        regex = r'x(\d{1,2})?s([a-fA-F0-9]{6}|[a-fA-F0-9]{3})="|\'(.*?)"|\''
    else:
        regex = r'x(\d{1,2})?([a-fA-F0-9]{6}|[a-fA-F0-9]{3})="(.*?)"'
    match = re.search(regex, f)
    if not match:
        return None, None, None
    return match.groups()
