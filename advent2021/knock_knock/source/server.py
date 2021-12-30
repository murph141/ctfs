#!/usr/bin/env python3

from __future__ import annotations
import asyncio
import random
import string
import hashlib
import time
import os

from flag import FLAG

TMOUT = 5
MINPORT = 25000
MAXPORT = 26000
DATADIR = "data"

def stripCrap(line):
    charset = string.ascii_lowercase + " " + string.digits
    return "".join([c for c in line.lower() if c in charset])

class KnockData():
    def __init__(self):
        self.data = {}
        self.songs = self.readSongs(DATADIR)

    def readSongs(self, dirname):
        onlyfiles = [f for f in os.listdir(
            dirname) if os.path.isfile(os.path.join(dirname, f))]

        out = {}

        for fn in onlyfiles:
            out[fn] = [x.strip()
                       for x in open(os.path.join(dirname, fn)).readlines()]

        return out

    async def _kickClient(self, ip: str, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, reason: str):
        cdata = f"Kick: {reason}\n"
        try:
            writer.write(cdata.encode())
            await writer.drain()
            writer.close()
            await writer.wait_closed()
        except:
            pass

    def removeClient(self, ip: str, full: bool = False):
        if ip in self.data:
            p = self.data[ip]["port"]
            self.data[ip]["active"] = False

            if full:
                del self.data[ip]

    async def addClient(self, ip: str, port: int, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> bool:
        kick = False
        if ip in self.data:
            nextport = self.data[ip]["nextport"]

            if self.data[ip]["active"]:
                kick = True
                oldreader = self.data[ip]["reader"]
                oldwriter = self.data[ip]["writer"]
                oldport = self.data[ip]["port"]
                del self.data[ip]
        else:
            nextport = MINPORT

        if kick:
            await asyncio.gather(
                self._kickClient(ip, oldreader, oldwriter,
                                 f"Already knocking on door {oldport} vs {port}"),
                self._kickClient(ip, reader, writer,
                                 f"Already knocking on door {oldport} vs {port}")
            )

            return False

        if port != nextport:
            await self._kickClient(ip, reader, writer, "Wrong door.")
            if ip in self.data:
                del self.data[ip]
            return False

        if ip in self.data:
            ts = self.data[ip]["ts"]
        else:
            ts = time.time()

        if ts + TMOUT < time.time():
            await self._kickClient(ip, reader, writer, "Too slow.")
            if ip in self.data:
                del self.data[ip]
            return False

        if ip not in self.data:
            self.data[ip] = {}
            self.data[ip]["expectedline"] = "knock knock"
            self.data[ip]["keepgoing"] = True

        self.data[ip]["active"] = True
        self.data[ip]["reader"] = reader
        self.data[ip]["writer"] = writer
        self.data[ip]["port"] = port
        self.data[ip]["ts"] = time.time()

        return True

    def getSongLine(self, song, line, orig=True):
        if song not in self.songs:
            return None, False

        lines = self.songs[song]
        if line < len(lines):
            if orig:
                return lines[line], True
            else:
                return stripCrap(lines[line]), True
        if line == len(lines):
            if random.randint(0, 100) < 25:
                return f"So beautiful, here is something for your trouble: {FLAG}", False
            else:
                return f"Thanks! You have a really nice voice.", False

        return None, False

    def advanceClient(self, ip):
        assert ip in self.data

        nextport = random.randrange(MINPORT, MAXPORT)
        self.data[ip]["nextport"] = nextport

        if "song" not in self.data[ip]:
            self.data[ip]["song"] = random.choice(list(self.songs.keys()))
            self.data[ip]["songline"] = 0
        else:
            self.data[ip]["songline"] += 1

        origline, _ = self.getSongLine(
            self.data[ip]["song"], self.data[ip]["songline"])

        expectedline, keepgoing = self.getSongLine(
            self.data[ip]["song"], self.data[ip]["songline"], orig=False)
        self.data[ip]["expectedline"] = expectedline

        if self.data[ip]["songline"] == 0:
            self.data[ip]["nextline"] = "Sing me this song...\n" + \
                origline + "\n"
        else:
            self.data[ip]["nextline"] = ""

        if keepgoing:
            s = f"{expectedline} -- {nextport}"
            h = hashlib.sha256(s.encode()).hexdigest()
            self.data[ip]["nextline"] += h
        else:
            self.data[ip]["nextline"] += expectedline

        self.data[ip]["keepgoing"] = keepgoing

    def get(self, ip: str, name: str):
        if ip in self.data:
            if name in self.data[ip]:
                return self.data[ip][name]

        return None


class KnockServer():
    def __init__(self, port: int, data: KnockData) -> None:
        self.port = port
        self.data = data

    async def _handle_tcp_client(self, reader: asyncio.StreamReader,
                                 writer: asyncio.StreamWriter):
        client_ip, _ = reader._transport.get_extra_info('peername')

        res = await self.data.addClient(client_ip, self.port, reader, writer)
        if not res:
            return

        expectedline = self.data.get(client_ip, "expectedline")

        fullremove = False
        try:
            writer.write(f"==[ Door {self.port} ]==\n".encode())
            await writer.drain()

            line = await reader.readline()
            line = stripCrap(line.decode().strip())

            if line == expectedline:
                self.data.advanceClient(client_ip)

                nextline = self.data.get(client_ip, "nextline")
                fullremove = not self.data.get(client_ip, "keepgoing")

                cdata = f"{nextline}\n".encode()
            else:
                if random.randint(0, 100) <= 33:
                    hint = f" (I wanted '{expectedline}')"
                else:
                    hint = ""
                cdata = f"That is not what I want to hear{hint}\n".encode()
                fullremove = True
            writer.write(cdata)
            await writer.drain()
        except Exception as e:
            fullremove = True
            print(f"fail! {e}")

        try:
            writer.close()
            await writer.wait_closed()
        except Exception as e:
            print(f"close fail! {e}")

        self.data.removeClient(client_ip, full=fullremove)

    async def run(self):
        serverh = await asyncio.start_server(self._handle_tcp_client, "0.0.0.0", self.port)
        await serverh.serve_forever()


async def main():
    d = KnockData()

    ports = range(MINPORT, MAXPORT)
    servers = [KnockServer(p, d).run() for p in ports]
    await asyncio.gather(*servers)

if __name__ == "__main__":
    asyncio.run(main())
