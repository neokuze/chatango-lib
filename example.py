#! /usr/bin/env python
# -*- coding: utf-8 -*-
import chatango
import asyncio
import time
import typing

class config:
    prefix = ['!']
    owner = ['theclonerx', 'neokuze']
    rooms = ['examplegroup']
    botuser = ['ExampleBot', ''] # password

class MyBot(chatango.Client):
    async def on_init(self):
        print("Bot initialized")
        
    async def on_start(self): # room join
        if config.rooms:
            for room in config.rooms:
                task = self.join(room)
                await asyncio.ensure_future(task)
            await asyncio.gather(*asyncio.all_tasks() - {asyncio.current_task()})
        else: print("config.rooms is empty")

    async def on_connect(self, room: typing.Union[chatango.Room, chatango.PM]):
        print(f"[{room.type}] Connected to", room)
       
    async def on_disconnect(self, room):
        print(f"[{room.type}] Disconnected from", room)

    async def on_room_denied(self, room):
        """
            This event get out when a room is deleted.
            self.rooms.remove(room_name)
        """
        print(f"[{room.type}] Rejected from", room,"\n ROOM must be deleted")
        
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
        message_content = message.body.split(' ')
        if len(message_content) < 1:
            cmd, args = message_content[0], message_content[1:]
        else:
            cmd, args = message_content[0], []
        if cmd[0] in config.prefix:
            use_prefix = True
            cmd = cmd[1:]
        else: use_prefix = False
        cmd = cmd.lower()
        if use_prefix:
            if cmd in ['hello', 'test', 'a']:
                await message.channel.send(f"Hello {message.user.showname}")

            elif cmd in ['j','join'] and args:
                if message.user.name in config.owners:
                    await self.join(args[0])
                else: await message.channel.send("{} is not in config.owners".format(messsage.user.name))
           
            elif cmd in ['l','leave'] and args:
                if message.user.name in config.owners:
                    await message.channel.send("Leaving {} requested by {}".format(args[0], messsage.user.name))
                    self.get_room(args[0])._reconnect = False
                    self.set_timeout(1, self.leave, args[0])
                else: await message.channel.send("{} is not in config.owners".format(messsage.user.name))
                    
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
