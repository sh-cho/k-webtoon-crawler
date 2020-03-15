import io
import json
import time
import re
import requests
import unicodedata
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from pathlib import Path
import PIL.Image
from bs4 import BeautifulSoup

NAVER_WEBTOON = {
    "FINISH_URL": "https://comic.naver.com/webtoon/finish.nhn",
    "LIST_URL": "https://comic.naver.com/webtoon/list.nhn?titleId=%s",
    "DETAIL_URL": "https://comic.naver.com/webtoon/detail.nhn?titleId=%s&no=%s"
}

last_status = {}


def update_last_index(_config, _item, _last_index):
    if _item['titleId'] not in _config['comics']:
        _config['comics'][_item['titleId']] = {'title': _item['title']}
        if 'titleOriginal' in _item:    # 원 제목 있는 경우 추가
            _config['comics'][_item['titleId']]['titleOriginal'] = _item['titleOriginal']
    _config['comics'][_item['titleId']]['lastIndex'] = _last_index
    return


def slugify(value, allow_unicode=False):
    """
    Convert to ASCII if 'allow_unicode' is False. Convert spaces to hyphens.
    Remove characters that aren't alphanumerics, underscores, or hyphens.
    Convert to lowercase. Also strip leading and trailing whitespace.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower()).strip()
    return re.sub(r'[-\s]+', '-', value)


###############################################################################################
if __name__ == "__main__":
    t = time.process_time()

    try:
        with open('config.json', 'r', encoding='UTF8') as f:
            config = json.load(f)
    except IOError:
        config = {"comics": {}}

    # HTTP Req header
    request_headers = {
        'User-agent': 'Mozilla/5.0'
    }

    # session
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.1,
        status_forcelist=[500, 502, 503, 504]
    )
    session.mount('http://', HTTPAdapter(max_retries=retries))

    # regex 패턴 셋업
    regex = re.compile(r'\d+')

    # 다운로드 폴더 생성
    download_dir = Path('.') / 'downloads'
    download_dir.mkdir(exist_ok=True)


    # 완결웹툰
    finish_webtoon_url = NAVER_WEBTOON["FINISH_URL"]
    soup = BeautifulSoup(session.get(finish_webtoon_url).text, 'lxml')

    # 웹툰 영역 찾기
    download_queue = []

    # 웹툰 영역에서 스토어에 가지 않은 완결웹툰 찾아 download_queue에 넣기
    webtoon_list = soup.select('.img_list li')
    for webtoon in webtoon_list:
        em = webtoon.find('em', class_='ico_store')
        if em is None:
            description = webtoon.find('a')
            webtoon_info = {
                'title': slugify(description['title'], allow_unicode=True),  # 파일 명 들어갈 수 없는 char 제거 (Windows / Linux)
                'titleId': regex.search(description['href']).group()
            }
            if webtoon_info['title'] is not description['title']:   # slugify로 제목 달라진 경우 원제목 추가
                webtoon_info['titleOriginal'] = description['title']
            download_queue.append(webtoon_info)

    try:
        # 한 작품씩 다운로드 시작
        for item in download_queue:
            # 작품 별 폴더 만들기
            title_dir = (download_dir / item['title'])
            title_dir.mkdir(exist_ok=True)

            # 마지막화 인덱스 구하기
            list_url = NAVER_WEBTOON["LIST_URL"] % item["titleId"]
            soup = BeautifulSoup(session.get(list_url).text, 'lxml')
            latest = soup.find('td', class_='title')
            last_index = int(regex.findall(latest.find_next('a')['href'])[1])

            # 이미 전부 다 다운받은거면 skip
            # 받고 나서 화 추가된 거 episode_index 설정
            if item['titleId'] in config['comics']:
                if config['comics'][item['titleId']]['lastIndex'] >= last_index:
                    continue
                else:
                    episode_index = config['comics'][item['titleId']]['lastIndex'] + 1
            else:
                episode_index = 1

            while True:
                if episode_index > last_index:  # 마지막화까지 받은 경우 다음 만화로 넘어가기
                    break

                # TODO: 1화부터 시작하지 않고 넘어갈 경우 체크
                # TODO: 로컬에 이미 받은 파일 있는 경우(&& size!=0인 경우) 스킵

                detail_url = NAVER_WEBTOON["DETAIL_URL"] % (item['titleId'], episode_index)

                # 이미지
                image_list = []
                full_width, full_height = 0, 0

                # select comics area
                soup = BeautifulSoup(session.get(detail_url).text, 'lxml')
                soup = soup.select('.wt_viewer img')

                # get every image
                for img in soup:
                    img_data = session.get(img['src'], headers=request_headers).content
                    img_name = Path(img['src']).name
                    im = PIL.Image.open(io.BytesIO(img_data))
                    width, height = im.size
                    image_list.append(im)
                    full_width = max(full_width, width)
                    full_height += height

                # concat images vertically
                canvas: PIL.Image = PIL.Image.new('RGB', (full_width, full_height), 'white')
                output_height = 0
                for im in image_list:
                    width, height = im.size
                    canvas.paste(im, (0, output_height))
                    output_height += height
                canvas.save(str(title_dir / ("%s_%04d화.png" % (item['title'], episode_index))), optimize=True)  # png optimize
                print("[%s] %04d / %04d 화" % (item['title'], episode_index, last_index))
                episode_index += 1

            # config 업데이트
            update_last_index(config, item, last_index)
            last_status = {"item": item, "lastIndex": last_index}

            print("--- [%s] download completed ---" % item['title'])
            break   # test
    except Exception as exc:
        print('*** error has occurred ***')
        print(exc)
        with open('error.log', 'w+', encoding='UTF8') as f:
            f.write(str(exc))
        update_last_index(config, last_status['item'], last_status['lastIndex'])
    finally:
        with open('config.json', 'w+', encoding='UTF8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)

    # elapsed time check
    t = time.process_time() - t
    print("%04d second(session) elapsed" % t)
    # main end