import chatango
import asyncio
import typing


class MyBot(chatango.Client):
    async def on_init(self):
        print("Bot initialized")
        await self.join("exampleroom")

    async def on_connect(self, room: typing.Union[chatango.Room, chatango.PM]):
        print("Connected to", room)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    bot = MyBot()
    bot.default_user("ExampleBot")
    loop.run_until_complete(bot.start())
    loop.run_forever()
