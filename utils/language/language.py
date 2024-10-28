from __future__ import annotations

from os import walk, path
from json import load
from logging import getLogger
from utils.database.cache import LRUCache

class LanguageManager(LRUCache):

    def __init__(self):
        super().__init__(780, -1)

    def add_language(self, category: str, language_data: dict) -> None:
        """Store language data for each category"""
        self.put(category, language_data)

    def get_language_key(self, category: str, key: str) -> str | None:
        """Get language data for category

        :returns str | None if not found

        """
        try:
            return self.get(category).get(key)
        except KeyError:
            return None

logger = getLogger(__name__)

class LocalizationManager:
    def __init__(self, locale_dir='translation'):
        self.locale_dir = locale_dir
        self.localizations: dict[str, LanguageManager] = {}
        self.load_localizations()

    def load_localizations(self, silent: bool = False):
        """Tải bản dịch vào bộ nhớ"""
        for root, dirs, files in walk(self.locale_dir):

            if root == self.locale_dir:
                continue

            language_code = path.basename(root)

            self.localizations[language_code] = LanguageManager()

            for filename in files:
                if filename.endswith('.json'):
                    filepath = path.join(root, filename)
                    with open(filepath, 'r', encoding='utf-8') as file:
                        category = filename[:-5]
                        data = load(file)
                        self.localizations[language_code].add_language(category, data)
                        if not silent:
                            logger.info(f"Loaded file {filename} for {language_code} language")

    def get(self, locale: str, categoryKey: str, key: str) -> str | None:
        """Lấy key bản dịch

        :returns str | None nếu key không tìm thấy

        """
        return self.localizations[locale].get_language_key(categoryKey, key)


if __name__ == '__main__':
    localization_manager = LocalizationManager()
    localization_manager.load_localizations()
    try:
        data = localization_manager.get('vi', 'music', 'no_avalible_next_track')
        print(data)
        data = localization_manager.get('vi', 'music', 'previous_track')
        print(data)
        data = localization_manager.get('vi', 'music', 'skip_track')
        print(data)
        data = localization_manager.get('vi', 'music', 'resumed')
        print(data)
        data = localization_manager.get("en", "language", "languageChange")
        print(data)
    except KeyError as e:
        print(e)
