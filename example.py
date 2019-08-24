import chatango
import asyncio
import typing

owners = ["neokuze"]
class MyBot(chatango.Client):
    async def on_init(self):
        print("Bot initialized")
        self.suffix = "~"
        await self.join("examplegroup")

    async def on_connect(self, room: typing.Union[chatango.Room, chatango.PM]):
        print("Connected to", room)

    async def on_message(self, message):
        if len(message.body.split(" ",1)) > 1:
            cmd = message.body.split(" ",1)[0].lower()
            args = message.body.split(" ",1)[1].strip().split(" ")
        else:
            cmd, args = message.body.split(" ",1)[0], []
        cmd = cmd[:-1]
        issuffix = message.body[len(cmd):len(cmd)+len(self.suffix)] == self.suffix
        print(f"[{message._room.name}]-[{issuffix}]-[{message.user}]: {message.body}")
        if issuffix:
            if cmd == "eval" and message.user.lower() in owners and args:
                try:
                    if args[0] == "await":
                        args = args[1:]
                        ret = await eval(" ".join(args))
                    else:
                        ret = eval(" ".join(args))
                    if ret == None:
                        await message._room.send_message("Done.")
                    else: await message._room.send_message(str(ret))
                except Exception as e:
                    print(str(e))
            elif cmd == "hello": # using version
                await message._room.send_message(f"Hello @{message.user}\rI\'m running chatango-lib {chatango.ver}'")
if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    bot = MyBot()
    bot.default_user("Yadrier")
    loop.run_until_complete(bot.start())
    loop.run_forever()
