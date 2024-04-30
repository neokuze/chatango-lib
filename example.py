#! /usr/bin/env python
# -*- coding: utf-8 -*-
import chatango
import asyncio
import time
import typing

class config:
    user_name = ""
    passwd = ""
    rooms = ["examplegroup"]
    pm = False

class Bot(chatango.Client):
    async def on_connect(self, room: typing.Union[chatango.Room, chatango.PM]):
        print("[info] Connected to {}".format(repr(room)))
    async def on_disconnect(self, room):
        print("[info] Disconnected from {}".format(repr(room)))
    async def on_message(self, message):
        print(time.strftime("%b/%d-%H:%M:%S", time.localtime(message.time)),
              message.room.name, message.user.showname, ascii(message.body)[1:-1])
        if message.body.split()[0] in ["!a"]:
            await message.room.send_message("test") 
       
"""
Specials thanks to LmaoLover, TheClonerx
"""
bot = Bot(config.user_name, config.passwd, config.rooms , pm=config.pm)
async def main ():
    await bot.run(forever=True)

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
        loop.run_forever()
    except KeyboardInterrupt:
        print("[KeyboardInterrupt] Killed bot.")
    finally:
        loop.close()
