import chatango
import asyncio
import typing
import random

class MyBot(chatango.Client):
    async def on_init(self):
        print("Bot initialized")
        await self.join("examplegroup")

    async def on_connect(self, room: typing.Union[chatango.Room, chatango.PM]):
        print("Connected to", room)

    async def on_message(self, message):
        print(message._room.name, message._user, ascii(message._body)[1:-1])
        if message._body.startswith("!a"):
            await message._room.send_message(f"Hello {message._user}")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    bot = MyBot()
    bot.default_user("examplebot")
    loop.run_until_complete(bot.start())
    loop.run_forever()
