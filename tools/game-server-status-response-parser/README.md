# Offline Game Server Status Response Parser

Read saved A2S_INFO and Quake 3 responses and report server and map names,
player counts, and capacity. A2S_INFO also reports the bot count and
several game metadata fields. Quake 3 player rows contribute to the count.
The CLI uses the Python standard library and prints JSON.

- [Source ZIP, SHA-256 checksums, and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/game-server-status-response-parser-v0.1.0)
- [Usage guide and fictional response files](SETUP.md)

All three original parser cases are preserved with fictional data.
Qualification covers Windows and Ubuntu with Python 3.12.16 and 3.15.2.
