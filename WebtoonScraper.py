import io
import re
import requests
import rsa
import shutil
import uuid
import lzstring
from PIL import Image
from typing import Optional
from urllib3.util.retry import Retry
from pathlib import Path
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup

from ScraperUtil import ScraperUtil


class WebtoonScraper:
    """
    Base class
    """
    def __init__(self):
        self.key = None
        self.s = None
        self.logged_in = False

    def login(self, input_id: Optional[str] = None, input_pw: Optional[str] = None) -> None:
        raise NotImplementedError

    def run(self) -> None:
        raise NotImplementedError


class NaverWebtoonScraper(WebtoonScraper):
    def __init__(self):
        super().__init__()
        # TODO
        self.key = "naver"
        self.urls = {
            "finish": "https://comic.naver.com/webtoon/finish.nhn",
            "list": "https://comic.naver.com/webtoon/list.nhn?titleId=%s",
            "detail": "https://comic.naver.com/webtoon/detail.nhn?titleId=%s&no=%s"
        }
        self.skip_list = {
            "714568",  # 2018 재생금지
            "696593",  # DEY 호러채널
            "578109",  # 러브슬립 2부
            "243316",  # 러브슬립
            "682222",  # 귀도
            "682803",  # 2016 비명
            "647948",  # 프린세스 5부
            "658823",  # 천국의 신화
            "655277",  # 고고고
            "657934",  # 2015 소름
            "490549",  # 2012 지구가 멸망한다면
            "440447",  # wish-마녀의 시간
            "440437",  # 투명살인
            "440439",  # 플라스틱 걸
            "350217",  # 2011 미스테리 단편
            "300957",  # 까치우는 날
            "301377",  # 뷰티플 게임
            "92106",   # 와라편의점 the animation
            "730811",  # 사소한 냐냐
        }

    def login(self, input_id: Optional[str] = None, input_pw: Optional[str] = None) -> None:
        def encrypt(key_str, uid, upw):
            def naver_style_join(l):
                return ''.join([chr(len(s)) + s for s in l])
            sessionkey, keyname, e_str, n_str = key_str.split(',')
            e, n = int(e_str, 16), int(n_str, 16)
            message = naver_style_join([sessionkey, uid, upw]).encode()
            pubkey = rsa.PublicKey(e, n)
            encrypted = rsa.encrypt(message, pubkey)
            return keyname, encrypted.hex()

        def encrypt_account(uid, upw):
            key_str = requests.get('https://nid.naver.com/login/ext/keys.nhn').content.decode("utf-8")
            return encrypt(key_str, uid, upw)

        self.s = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=0.1,
            status_forcelist=[500, 502, 503, 504],
        )

        self.s.mount('https://', HTTPAdapter(max_retries=retries))

        if input_id is not None and input_pw is not None:
            request_headers = {'User-agent': 'Mozilla/5.0'}
            bvsd_uuid = uuid.uuid4()
            encData = '{"a":"%s-4","b":"1.3.4","d":[{"i":"id","b":{"a":["0,%s"]},"d":"%s","e":false,"f":false},{"i":"%s","e":true,"f":false}],"h":"1f","i":{"a":"Mozilla/5.0"}}' % (
            bvsd_uuid, input_id, input_id, input_pw)
            bvsd = '{"uuid":"%s","encData":"%s"}' % (bvsd_uuid, lzstring.LZString.compressToEncodedURIComponent(encData))

            encnm, encpw = encrypt_account(input_id, input_pw)
            resp = self.s.post("https://nid.naver.com/nidlogin.login", data={
                "svctype": "0",
                "enctp": "1",
                "encnm": encnm,
                "enc_url": "http0X0.0000000000001P-10220.0000000.000000www.naver.com",
                "url": "www.naver.com",
                "smart_level": "1",
                "encpw": encpw,
                "bvsd": bvsd
            }, headers=request_headers)

            finalize_url = re.search(r'location\.replace\("([^"]+)"\)', resp.content.decode("utf-8")).group(1)
            self.s.get(finalize_url)
        else:
            # TODO
            raise NotImplementedError

    def run(self) -> None:
        # TODO: 코드 정리 (개판임)
        assert self.s is not None

        request_headers = {"User-agent": "Mozilla/5.0"}
        id_regex = re.compile(r"\d+")

        # 다운로드 폴더 생성
        download_dir = Path(".") / "downloads"
        download_dir.mkdir(exist_ok=True)

        # 완결웹툰
        finish_webtoon_url = self.urls["finish"]
        soup = BeautifulSoup(self.s.get(finish_webtoon_url).text, "lxml")

        # 웹툰 영역에서 스토어에 가지 않은 완결웹툰 찾아 download_queue에 넣기
        download_queue = []
        webtoon_list = soup.select(".img_list li")
        for webtoon in webtoon_list:
            em = webtoon.find("em", class_="ico_store")
            if em is None:
                description = webtoon.find('a')
                webtoon_info = {
                    'title': ScraperUtil.slugify(description['title'], allow_unicode=True),
                    'titleId': id_regex.search(description['href']).group()
                }
                if webtoon_info['titleId'] in self.skip_list:  # 다운로드 스킵
                    continue
                elif webtoon_info['title'] != description['title']:  # slugify로 제목 달라진 경우 원제목 추가
                    webtoon_info['titleOriginal'] = description['title']
                download_queue.append(webtoon_info)

        print("download queue 생성 완료")

        try:
            # 한 작품씩 다운로드 시작
            for item in download_queue:
                print("--- [%s] download start ---" % item['title'])
                # 마지막화 인덱스 구하기
                list_url = self.urls["list"] % item["titleId"]
                soup = BeautifulSoup(self.s.get(list_url).text, 'lxml')
                latest = soup.find('td', class_='title')
                last_index = int(id_regex.findall(latest.find_next('a')['href'])[1])

                # 이미 전부 다 다운받은거면 skip
                # 받고 나서 화 추가된 거 episode_index 설정
                if item['titleId'] in ScraperUtil.download_history.get(self.key):
                    if ScraperUtil.download_history[self.key][item['titleId']]['lastIndex'] >= last_index:
                        continue
                    else:
                        episode_index = ScraperUtil.download_history[self.key][item['titleId']]['lastIndex'] + 1
                else:
                    episode_index = 1

                # print("[%s] current_index:%d last_index:%d" % (item['title'], config['comic'][item['titleId']]['lastIndex'], last_index))

                # 작품 별 폴더 만들기
                title_dir = (download_dir / item['title'])
                title_dir.mkdir(exist_ok=True)

                # 한 화씩 다운로드
                while True:
                    if episode_index > last_index:  # 마지막화까지 받은 경우 다음 만화로 넘어가기
                        break

                    detail_url = self.urls["detail"] % (item['titleId'], episode_index)

                    # 이미지
                    image_list = []
                    full_width, full_height = 0, 0

                    # select comics area
                    soup = BeautifulSoup(self.s.get(detail_url).text, 'lxml')
                    soup = soup.select('.wt_viewer img')

                    # get every image
                    for img in soup:
                        # img_data 오류날 경우 (아무것도 없을 때) -> 다시 받기
                        while True:
                            img_req = self.s.get(img['src'], headers=request_headers)
                            if img_req.status_code == 200:
                                img_data = img_req.content
                                break
                        img_name = Path(img['src']).name
                        im = Image.open(io.BytesIO(img_data))
                        width, height = im.size
                        image_list.append(im)
                        full_width = max(full_width, width)
                        full_height += height

                    # concat images vertically
                    canvas = Image.new('RGB', (full_width, full_height), 'white')
                    output_height = 0
                    for im in image_list:
                        width, height = im.size
                        canvas.paste(im, (0, output_height))
                        output_height += height
                    canvas.save(str(title_dir / ("%s_%04d화.png" % (item['title'], episode_index))),
                                optimize=True)  # png optimize
                    print("[%s] %04d / %04d 화" % (item['title'], episode_index, last_index))

                    ScraperUtil.update_download_history(self.key, item, episode_index)
                    ScraperUtil.save_download_history()
                    episode_index += 1

                print("--- [%s] download completed ---" % item['title'])

                # 남은 용량 200GB 미만일 경우 종료
                # TODO
                total, used, free = shutil.disk_usage("C:")
                if free // (2 ** 30) < 200:
                    print("--- remaining capacity is less than 200GB ---")
                    break
        except Exception as exc:
            print('*** error has occurred ***')
            print(exc)


# TODO: DaumWebtoonScraper
# TODO: WebtoonsDotcomScraper