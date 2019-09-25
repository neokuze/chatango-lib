#! /usr/bin/env python
# -*- coding: utf-8 -*-
import chatango
import asyncio
import typing
import random


class MyBot(chatango.Client):
    async def on_init(self):
        print("Bot initialized")
        await self.join("examplebot")

    async def on_connect(self, room: typing.Union[chatango.Room, chatango.PM]):
        print("Connected to", room)

    async def on_room_init(self, room):
        if room.user.isanon:
            room.setFont("namecolor", "000000")
            room.setFont("fontcolor", "000000")
            room.setFont("fontsize", 11)
            room.setFont("fontface", 1)
        else:
            await room.user.get_profile()
        
    async def on_message(self, message):
        print(message.room.name, message.user.showname,
              ascii(message.body)[1:-1])
        if message.body.startswith("!a"):
            await message._room.send_message(f"Hello {message.user.showname}")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    bot = MyBot()
    bot.default_user("examplebot", pm=False)
    loop.run_until_complete(bot.start())
    loop.run_forever()
