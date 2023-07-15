#! /usr/bin/env python
# -*- coding: utf-8 -*-
import chatango
import asyncio
import time
import typing

class config:
    user_name = ""
    passwd = ""
    rooms = ["asynclibraryinpython"]
    pm = False

class MyBot(chatango.Client):
    async def on_connect(self, room: typing.Union[chatango.Room, chatango.PM]):
        print("[info] Connected to {}".format(repr(room)))
       
    async def on_disconnect(self, room):
        print("[info] Disconnected from {}".format(repr(room)))
   async def on_message(self, message):
        print(f"[{message.room.name}] {message.time} {message.user.name} {message.body}")
       
"""
Specials thanks to LmaoLover, TheClonerx
"""

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bot = Bot(config.user_name, config.passwd, config.rooms , pm=config.pm)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(bot.run(forever=True))
        loop.run_forever()
    except KeyboardInterrupt:
        print("[KeyboardInterrupt] Killed bot.")
    finally:
        loop.close()
