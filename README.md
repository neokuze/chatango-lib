# chatango-lib

A powerful asynchronous Chatango library with aiohttp, written in Python 3.6+

### Library is supposed to be similar in usage for megach.py users, but was based on cherryblossom.

Special thanks to [Sweets](https://github.com/sweets/), [Linkkg](https://github.com/linkkg/megach.py), and [TheClonerx](https://github.com/theclonerx).

Similar usage to "megach.py" by Linkkg & "CherryBlossom" by Sweets. Sweets also motivated me with async, & thanks to [LmaoLover](https://github.com/LmaoLover/) for their help.

---
#### supposed to be working
##### Rooms/reconnect

##### PM/DM

##### Websocket raise exceptions on close ws.

---
##### Things to know (TO DO)
[☑️] Proper way to handle ws error. 

[☑️] Disconnect event.

[ ] Reimplement reconnect events.

[ ] Fixed PM youtube video message.

[ ] Documentation.

[ ] Example with aiofiles

---
**Requirements:**

1. Python 3.6+
2. Setuptools or pip for dependencies (e.g., aiohttp)
3. A little knowledge of asyncio
---
## How to install
### Linux / Termux
`git clone https://github.com/neokuze/chatango-lib && cd chatango-lib`
### wherever is the setup.py
`$ pip install --user -r requirements.txt`

`$ pip install --user .`
