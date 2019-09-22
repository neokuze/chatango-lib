import chatango
import asyncio
import typing
import random

owners = ["theclonerx","neokuze"]
class MyBot(chatango.Client):
    async def on_init(self):
        print("Bot initialized")
        await self.join("examplegroup")

    async def on_connect(self, room: typing.Union[chatango.Room, chatango.PM]):
        print("Connected to", room)

    async def onmessage(self, message):
        print(message.room.name, message.user.showname, ascii(message.body)[1:-1])
        if message.body.startswith("!a"):
            await message._room.send_message(f"Hello {message.user.showname}")
        elif message.user.name in owners and message.body.split(" ")[0] == "!e" and message.body.split(" ") > 1:
            try:
                if message.body.split(" ")[1] == "await":
                    ret = await eval(" ".join(message.body.split(" ")[2:]))
                else:
                    ret = eval(" ".join(message.body.split(" ")[1:]))
            except Exception as ret:
                print('3rr0r: ', ret)
            await message.room.send_messsge(ret, html=False)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    bot = MyBot()
    bot.default_user("examplebot", pm=False)
    loop.run_until_complete(bot.start())
    loop.run_forever()
