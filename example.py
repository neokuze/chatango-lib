#! /usr/bin/env python
# -*- coding: utf-8 -*-
import chatango
import asyncio
import time
import typing

class config:
    prefix = ['!']
    owners = ['theclonerx', 'neokuze']
    rooms = ['visudo','sudoers']
    botuser = ['ExampleBot', ''] # password

class MyBot(chatango.Client):
    async def on_init(self):
        print("[info] Bot started...")

    async def on_start(self):
        if config.rooms:
            for room in config.rooms:
                task = self.join(room)
                await asyncio.ensure_future(task)
            await asyncio.gather(*asyncio.all_tasks() - {asyncio.current_task()})
            print("[info] Bot has joined sucessfully all the rooms")
        else:
            print("[info] config.rooms is empty.")

    async def on_connect(self, room: typing.Union[chatango.Room, chatango.PM]):
        print("[info] Connected to {}".format(repr(room)))
       
    async def on_disconnect(self, room):
        print("[info] Disconnected from {}".format(repr(room)))

    async def on_room_denied(self, room):
        """
            This event get out when a room is deleted.
            self.rooms.remove(room_name)
        """
        print("[info] Rejected from {},".format(repr(room))," ROOM must be deleted.")
        
    async def on_room_init(self, room):
        if room.user.isanon:
            room.set_font(
                name_color = "000000",
                font_color = "000000",
                font_face  = 1,
                font_size  = 11
            )
        else:
            await room.user.get_profile()
            await room.enable_bg()
            
    async def on_message(self, message):
        print(time.strftime("%b/%d-%H:%M:%S", time.localtime(message.time)),
              message.room.name, message.user.showname, ascii(message.body)[1:-1])
        message_content = message.body
        if len(message_content.split()) > 1:
            cmd, args = message_content.split(" ", 1)
            args = args.split()
        else:
            cmd, args = message_content, []
        cmd = cmd.lower()
        if cmd[0] in config.prefix:
            use_prefix = True
            cmd = cmd[1:]
        else: 
            use_prefix = False
        if use_prefix:
            if cmd in ['hello', 'test', 'a']:
                await message.channel.send(f"Hello {message.user.showname}")

            elif cmd in ['j','join'] and args:
                if message.user.name in config.owners:
                    await self.join(args[0])
                    await message.channel.send(f"I was connected to {args[0]}")
                else: 
                    await message.channel.send("{} is not in config.owners".format(messsage.user.name))
           
            elif cmd in ['l','leave'] and args:
                room = args[0]
                if message.user.name in config.owners:
                    await message.channel.send("Leaving {} requested by {}".format(room, message.user.name))
                    self.get_room(room).change_reconnect # Just set _reconnect to False
                    self.set_timeout(1, self.leave, room, False)
                else: 
                    await message.channel.send("{} is not in config.owners".format(message.user.name))

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    bot = MyBot()
    bot.default_user(config.botuser[0], config.botuser[1]) # easy_start
#     or_accounts = [["user1","passwd1"], ["user2","passwd2"]]
#     bot.default_user(accounts=or_accounts, pm=False) #True if passwd was input.
    ListBots = [bot.start()] # Multiple instances 
    task = asyncio.gather(*ListBots, return_exceptions=True)
    try:
        loop.run_until_complete(task)
        loop.run_forever()
    except KeyboardInterrupt:
        print("[KeyboardInterrupt] Killed bot.")
    finally:
        task.cancel()
        loop.close()
