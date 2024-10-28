from __future__ import annotations
from utils.database.cache import LRUCache


class LyricCache(LRUCache):
    def __init__(self):
        super().__init__(2000, 600)

    def add_lyric(self, song_name: str, lyric_data: dict):
        try:
            data = self.get(song_name)
        except KeyError:
            data = None
        if data is None:
            self.put(song_name, lyric_data)

    def get_lyric(self, song_name: str) -> dict | None:
        try:
            return self.get(song_name)
        except KeyError:
            return None