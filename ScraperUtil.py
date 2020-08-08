import json
import re
from unicodedata import normalize


class ScraperUtil:
    # Static variable
    account_info = {}
    download_history = {"naver": {}, "daum": {}}

    def __init__(self):
        pass

    @staticmethod
    def slugify(value, allow_unicode=False) -> str:
        """
        Convert to ASCII if 'allow_unicode' is False. Convert spaces to hyphens.
        Remove characters that aren't alphanumerics, underscores, or hyphens.
        Convert to lowercase. Also strip leading and trailing whitespace.
        """
        value = str(value)
        if allow_unicode:
            value = normalize('NFKC', value)
        else:
            value = normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
        value = re.sub(r'[^\w\s-]', '', value.lower()).strip()
        return re.sub(r'[-\s]+', '-', value)

    @staticmethod
    def load_accounts(filename: str = "accounts.json") -> None:
        try:
            with open(filename, "r", encoding="UTF8") as f:
                ScraperUtil.account_info = json.load(f)
        except IOError:
            pass

    @staticmethod
    def load_download_history(filename: str = "download_history.json") -> None:
        try:
            with open(filename, "r", encoding="UTF8") as f:
                ScraperUtil.download_history = json.load(f)
        except IOError:
            pass

    @staticmethod
    def save_download_history(filename: str = "download_history.json") -> None:
        try:
            with open(filename, "w", encoding="UTF8") as f:
                json.dump(ScraperUtil.download_history, f, ensure_ascii=False, indent=4)
        except IOError:
            pass

    @staticmethod
    def update_download_history(key: str, webtoon: dict, last_index: int) -> None:
        if webtoon["titleId"] not in ScraperUtil.download_history[key]:
            ScraperUtil.download_history[key][webtoon["titleId"]] = {"title": webtoon["title"]}
            if "titleOriginal" in webtoon:
                ScraperUtil.download_history[key][webtoon["titleId"]]["titleOriginal"] = webtoon["titleOriginal"]
        ScraperUtil.download_history[key][webtoon["titleId"]]["lastIndex"] = last_index