#! /usr/bin/env python
# -*- coding: utf-8 -*-
import chatango
import asyncio
import time

class config:
    user_name = ""
    passwd = ""
    rooms = ["asynclibraryinpython"]
    pm = False

class Bot(chatango.Client):
    async def on_connect(self, room):
        print("[info] Connected to {}".format(repr(room)))
        await room.set_bg_mode(1) #enable premium bg.

    async def on_pm_connect(self, pm):
        print("[info] Connected to {}".format(repr(pm)))
        await pm.enable_bg() #enable premium bg for pm

    async def on_disconnect(self, room):
        print("[info] Disconnected from {}".format(repr(room)))

    async def on_pm_disconnect(self, pm):
        print("[info] Disconnected from {}".format(repr(pm)))

    async def on_message(self, message):
        print(time.strftime("%b/%d-%H:%M:%S", time.localtime(message.time)),
              message.room.name, message.user.showname, ascii(message.body)[1:-1])
        if message.body.split()[0] in ["!a"]:
            await message.room.send_message("test", html=True) 

    async def on_pm_message(self, message):
        print(time.strftime("%b/%d-%H:%M:%S", time.localtime(message.time)),
              message.room.name, message.user.showname, ascii(message.body)[1:-1])
        if message.body.split()[0] in ["!a"]:
            await message.room.send_message(message.user.name, "test")
            
    async def on_room_denied(self, room): # remove denied rooms from self.rooms
        if room.name in self.rooms:
            self.leave_room(room.name)
            if self.get_room(room.name):
                del self.rooms[room.name]
                print('[info] removed denied room: ', room.name)

       
"""
Specials thanks to LmaoLover, TheClonerx
"""
bot = Bot(config.user_name, config.passwd, config.rooms , pm=config.pm)
async def main():
    await bot.run(forever=True)

async def stop():
    await bot.stop()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
        loop.run_forever()
    except KeyboardInterrupt:
        print("[KeyboardInterrupt] Killed bot.")
    finally:
        loop.run_until_complete(stop())
        loop.close()
