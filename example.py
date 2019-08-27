import chatango
import asyncio
import typing
import random

owners = ["neokuze", "theclonerx"]


class MyBot(chatango.Client):
    async def on_init(self):
        print("Bot initialized")
        self.suffix = "/"
        await self.join("examplegroup")

    async def on_connect(self, room: typing.Union[chatango.Room, chatango.PM]):
        print("Connected to", room)

    async def on_message(self, message):
        if len(message._body.split(" ", 1)) > 1:
            cmd = message._body.split(" ", 1)[0].lower()
            args = message._body.split(" ", 1)[1].strip().split(" ")
        else:
            cmd, args = message._body.split(" ", 1)[0], []
        cmd = cmd[:-1]
        issuffix = message._body[len(cmd):len(
            cmd)+len(self.suffix)] == self.suffix
        print(
            f"[{message._room.name}]-[{issuffix}]-[{message._user}]: {message._body}")
        if issuffix:
            if cmd == "hello":  # using version
                await message._room.send_message(f"Hello @{message._user}\rI\'m running chatango-lib {chatango.ver}\nOwners:{', '.join(owners)}")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    bot = MyBot()
    bot.default_user("examplebot")
    loop.run_until_complete(bot.start())
    loop.run_forever()
