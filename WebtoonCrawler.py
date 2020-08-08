from WebtoonScraper import NaverWebtoonScraper
from ScraperUtil import ScraperUtil


class WebtoonCrawler:
    def __init__(self):
        self.scrapers = []

    def load(self, accounts_filename: str = "accounts.json",
             download_history_filename: str = "download_history.json") -> None:
        ScraperUtil.load_accounts(accounts_filename)
        ScraperUtil.load_download_history(download_history_filename)

    def run(self) -> None:
        self.scrapers.append(NaverWebtoonScraper())

        try:
            for sc in self.scrapers:
                account = ScraperUtil.account_info[sc.key]
                my_id, my_pw = account["id"], account["pw"]
                sc.login(my_id, my_pw)
                sc.run()
        except Exception as e:
            # TODO: 클린한 예외처리
            print(e)
        finally:
            pass