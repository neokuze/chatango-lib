#! /usr/bin/env python
# -*- coding: utf-8 -*-
import chatango
import asyncio
import time
import typing

class MyBot(chatango.Client):
    async def on_init(self):
        print("Bot initialized")
        await self.join("examplegroup")

    async def on_connect(self, room: typing.Union[chatango.Room, chatango.PM]):
        print("Connected to", room)
       
    async def on_disconnect(self, room):
        print(f"Disconnected from {room}")

    async def on_room_init(self, room):
        if room.user.isanon:
            room.setFont(
                name_color = "000000",
                font_color = "000000",
                font_face  = 1,
                font_size  = 11
            )
        else:
            await room.user.get_main_profile()
            await room.enable_bg()
            
    async def on_message(self, message):
        print(time.strftime("%b/%d-%H:%M:%S", time.localtime(message.time)),
              message.room.name, message.user.showname, ascii(message.body)[1:-1])
        
        if message.body.startswith("!a"):
            await message.channel.send(f"Hello {message.user.showname}")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    bot = MyBot()
    bot.default_user("examplebot", pm=False) #True if passwd was input.
    ListBots = [bot.start()]
    task = asyncio.gather(*ListBots, return_exceptions=True)
    try:
        loop.run_until_complete(task)
        loop.run_forever()
    except KeyboardInterrupt:
        print("[KeyboardInterrupt] Killed bot.")
    finally:
        task.cancel()
        loop.close()
