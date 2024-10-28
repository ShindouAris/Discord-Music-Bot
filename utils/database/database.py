import os
from logging import getLogger

import aiosqlite
from typing import TypedDict, Optional
from asyncio import sleep, create_task

logger = getLogger(__name__)

class Database_template(TypedDict):
    language: str
    synced: bool

class Cached_Databases:
    databases: dict[int, Database_template] = {}

    async def __commit_all__(self):
        while True:
            count = 0
            for guildID, guildData in self.databases.items():
                if not guildData["synced"]:
                    await self.database.set_guild(guildID, guildData["language"])
                    guildData["synced"] = True
                    count += 1
            if count:
                logger.info(f"Đã đồng bộ {count} guilds lên database")
            await sleep(600)

    def __init__(self, database):
        self.database = database
        create_task(self.__commit_all__())

    async def add_guild(self, guildID: int, language: str = "vi"):
        await self.database.create_guild(guildID, language)
        self.databases[guildID] = {}
        self.databases[guildID]['language'] = language
        self.databases[guildID]['synced'] = True

    async def get_language(self, guildID: int):
        if not guildID in self.databases:
            db_data = await self.database.get_guild(guildID)
            if db_data is None:
                await self.add_guild(guildID)
                return 'vi'
            self.databases[guildID] = {}
            self.databases[guildID]['language'] = db_data
            self.databases[guildID]['synced'] = True
            return db_data
        return self.databases[guildID]['language']

    async def delete_guild(self, guildID: int):
        self.databases.pop(guildID)
        await self.database.delete_guild(guildID)

    async def update_guild(self, guildID: int, language: str = "vi"):
        if not guildID in self.databases:
            return await self.add_guild(guildID, language)
        self.databases[guildID]['language'] = language
        self.databases[guildID]['synced'] = False

    async def close(self):
        logger.info("Đang lưu dữ liệu...")
        count = 0
        for guildID in self.databases:
            if not self.databases[guildID]['synced']:
                await self.database.set_guild(guildID, self.databases[guildID]['language'])
                count += 1
        logger.info(f"Đã đồng bộ {count} guild{'s' if count > 1 else ''} vào cơ sở dữ liệu")


class Local_Database:
    def __init__(self):
        self.cached_databases: Optional[Cached_Databases] = None

    def initialze(self):
        path = 'databases/'
        if not os.path.exists(path):
            os.makedirs(path)

        self.cached_databases = Cached_Databases(self)

    async def build_table(self):
        async with aiosqlite.connect("databases/guildData.sqlite") as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS guilds(
                    guildID INTEGER PRIMARY KEY, 
                    language TEXT DEFAULT 'vi'
                )
            """)
            await db.commit()
            await db.close()

    async def create_guild(self, guildID: int, language: str = "vi"):
        async with aiosqlite.connect("databases/guildData.sqlite") as cursor:
            await cursor.execute(
                """INSERT INTO guilds(guildID, language) VALUES (?, ?)""",
                (guildID, language,)
            )
            await cursor.commit()
            await cursor.close()

    async def get_guild(self, guildID: int):
        async with aiosqlite.connect("databases/guildData.sqlite") as db:
            cursor = await db.execute(
                """SELECT language FROM guilds WHERE guildID=?""",
                (guildID,)
                )
            data = await cursor.fetchone()
            await db.close()
            return data[0] if data else None

    async def delete_guild(self, guildID: int):
        async with aiosqlite.connect("databases/guildData.sqlite") as cursor:
            await cursor.execute(
                """DELETE FROM guilds WHERE guildID=?""",
                (guildID,)
            )
            await cursor.commit()
            await cursor.close()

    async def set_guild(self, guildID: int, language: str = None):
        if not language:
            language = "vi"
        async with aiosqlite.connect("databases/guildData.sqlite") as cursor:
            await cursor.execute("""UPDATE guilds SET language=? WHERE guildID=?""", (language, guildID,))
            await cursor.commit()
            await cursor.close()

