from __future__ import annotations
import asyncio

from motor.motor_asyncio import AsyncIOMotorClient
from copy import deepcopy
from .cache import LRUCache
from logging import getLogger

class DB:
    users = "users"

userDB = {
    DB.users: {
        "version": 0.1,
        "playlist": [
            # {
            # "name": None,
            # "tracks": []
            # }
        ],
        "last_played": [
        #     {
        #     "name": None,
        #     "url": None
        # }
        ]
    }
}

logger = getLogger(__name__)

class CacheNode(LRUCache):
    def __init__(self):
        super().__init__(7000, -1)
        self.lock = asyncio.Lock()

    async def add_userData(self, userID, data):
        self.put(userID, data)

    async def get_userData(self, userID) -> dict | None:
        try:
            return self.get(userID)
        except KeyError:
            return None

    async def get_last_played(self, userID) -> list | None:
        try:
            return self.get(userID)['last_played']
        except KeyError:
            return None

    async def update_last_played(self, userID, data):
        try:
            user_data = await self.get_userData(userID)
            if not user_data:
                return False
            if len(user_data['last_played']) >= 6:
                user_data['last_played'].pop(0)
            user_data['last_played'].append(data)
            self.put(userID, user_data)
            return True
        except Exception:
            return False



class Base:

    @staticmethod
    def get_default_data(db: DB.users):
        return deepcopy(userDB[db])


class UserData(Base):

    def __init__(self, token: str, timeout = 10):
        super().__init__()
        self.cache = CacheNode()

        self.client: AsyncIOMotorClient = AsyncIOMotorClient(token, connectTimeoutMS=timeout*1000)
        logger.info("Đã kết nối tới cơ sở dữ liệu: %s", token)


    async def get_data(self, id_: int, db: DB.users):
        try:
            data = await self.client['user_db'][db].find_one({"_id": id_})
        except:
            data = {}

        return data

    async def query_user_data_by_id(self, id_: int, db: DB.users):
        data = await self.cache.get_userData(id_)
        if not data:
            remote = await self.client['user_db'][db].find_one({"_id": id_})
            if not remote:
                remote = self.get_default_data(db)
                remote['_id'] = id_
                await self.client['user_db'][db].insert_one(remote)
            await self.cache.add_userData(id_, remote)
            return remote
        return data


    async def update_data(self, id_: int, data: dict, db: DB.users):
        await self.client['user_db'][db].update_one({"_id": id_}, {"$set": data})
        return True

    async def delete_data(self, id_: int, db: DB.users):
        await self.client['user_db'][db].delete_one({"_id": id_})
        return True

    async def insert_data(self, id_: int, data: dict, db: DB.users):
        await self.client['user_db'][db].insert_one({"_id": id_, "data": data})
        return True

    async def get_playlist(self, id_: int, db: DB.users):
        data = await self.get_data(id_, db)
        return data.get("playlist", None)

    async def add_playlist(self, id_: int, data: list, db: DB.users):
        await self.client['user_db'][db].update_one({"_id": id_}, {"$push": {"playlist": {"$each": data}}})

    async def remove_playlist(self, id_: int, playlistName: str, db: DB.users):
        result = await self.client['user_db'][db].update_one({"_id": id_}, {"$pull": {"playlist": {"name": playlistName}}})
        return result.modified_count > 0

    async def get_played_tracks(self, id_: int, db: DB.users):
        logger.info("Getting playedTrack")
        data = await self.cache.get_last_played(id_)
        if not data:
            remote_data = await self.client['user_db'][db].find_one({"_id": id_})
            if remote_data is None:
                return None
            data = remote_data.get("last_played", None)
            await self.query_user_data_by_id(id_, db)
        logger.info(data)
        return data

    async def add_last_played(self, id_: int, track: dict, db: DB.users):
        logger.info("Adding track: %s to %s Database", track, db)
        cached_update = await self.cache.update_last_played(id_, track)
        logger.info("Done: update_cache")
        if not cached_update:
            remote = await self.query_user_data_by_id(id_, db)
            logger.info("Done: task query")
            if remote:
                await self.cache.update_last_played(id_, track)
                logger.info("Done: task update from remote")

        await self.client['user_db'][db].update_one({"_id": id_}, {"$push": {"last_played": track}})
        await self.remove_last_played(id_, db)
        logger.info("Done: task update from database")

    async def remove_last_played(self, id_: int, db: DB.users):
        track = await self.get_played_tracks(id_, db)
        if len(track) >= 6:
            await self.client['user_db'][db].update_one({"_id": id_}, {"$pop": {"last_played": 1}})