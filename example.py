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
        print(message.room.name, message._user, ascii(message.body)[1:-1])
        if message.body.startswith("!a"):
            await message._room.send_message(f"Hello {message.user}")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    bot = MyBot()
    bot.default_user("examplebot", pm=False)
    loop.run_until_complete(bot.start())
    loop.run_forever()
