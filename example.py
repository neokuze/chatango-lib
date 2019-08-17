import chatango
import asyncio


class MyBot(chatango.Client):
    async def on_event(self, event, *args, **kwargs):
        print(event, args, kwargs)

    async def on_init(self):
        print("Bot initialized")
        await self.join("exampleroom")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    bot = MyBot()
    bot.default_user("MyBot")
    loop.run_until_complete(bot.start())
    loop.run_forever()
