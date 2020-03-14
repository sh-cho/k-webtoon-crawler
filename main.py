import io
import json
import time
import re
import requests
import PIL.Image
from pathlib import Path

from PIL.Image import Image
from bs4 import BeautifulSoup

NAVER_WEBTOON = {
    "FINISH_URL": "https://comic.naver.com/webtoon/finish.nhn",
    "LIST_URL": "https://comic.naver.com/webtoon/list.nhn?titleId=%s",
    "DETAIL_URL": "https://comic.naver.com/webtoon/detail.nhn?titleId=%s&no=%s"
}

t = time.process_time()

###############################################################################################
if __name__ == "__main__":
    # TODO: 설정
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except IOError:
        config = {}

    # regex 패턴 셋업
    regex = re.compile(r'\d+')

    # 다운로드 폴더 생성
    download_dir = Path('.') / 'downloads'
    download_dir.mkdir(exist_ok=True)

    # HTTP Req header
    request_headers = {
        'User-agent': 'Mozilla/5.0'
    }

    # 완결웹툰
    finish_webtoon_url = NAVER_WEBTOON["FINISH_URL"]
    soup = BeautifulSoup(requests.get(finish_webtoon_url).text, 'lxml')

    # 웹툰 영역 찾기
    download_queue = []

    # 웹툰 영역에서 스토어에 가지 않은 완결웹툰 찾아 download_queue에 넣기
    webtoon_list = soup.select('.img_list li')
    for webtoon in webtoon_list:
        em = webtoon.find('em', class_='ico_store')
        if em is None:
            description = webtoon.find('a')
            webtoon_info = {
                'title': description['title'],
                'titleId': regex.search(description['href']).group()
            }
            download_queue.append(webtoon_info)

    # TODO: 다운로드 내역과 비교해서 download queue 정리

    # 한 작품씩 다운로드 시작
    for item in download_queue:
        title_dir = (download_dir / item['title'])
        title_dir.mkdir(exist_ok=True)

        # 마지막화 인덱스 구하기
        list_url = NAVER_WEBTOON["LIST_URL"] % item["titleId"]
        soup = BeautifulSoup(requests.get(list_url).text, 'lxml')
        latest = soup.find('td', class_='title')
        last_index = int(regex.findall(latest.find('a')['href'])[1])

        # 화 별 다운로드
        episode_index = 1
        while True:
            if episode_index > last_index:    # 마지막화까지 받은 경우 다음 만화로 넘어가기
                break

            # TODO: 1화부터 시작하지 않고 넘어갈 경우 체크

            detail_url = NAVER_WEBTOON["DETAIL_URL"] % (item['titleId'], episode_index)

            # 이미지
            image_list = []
            full_width, full_height = 0, 0

            # download
            soup = BeautifulSoup(requests.get(detail_url).text, 'lxml')
            soup = soup.select('.wt_viewer img')
            # image_index = 1

            for img in soup:
                img_data = requests.get(img['src'], headers=request_headers).content
                img_name = Path(img['src']).name
                im = PIL.Image.open(io.BytesIO(img_data))
                width, height = im.size
                image_list.append(im)
                full_width = max(full_width, width)
                full_height += height
                # image_index += 1

            # concat images vertically
            canvas: Image = PIL.Image.new('RGB', (full_width, full_height), 'white')
            output_height = 0
            for im in image_list:
                width, height = im.size
                canvas.paste(im, (0, output_height))
                output_height += height
            canvas.save(str(title_dir / ("%s_%04d화.png" % (item['title'], episode_index))))

            episode_index += 1
            # exit(315)

        # TODO: config에 from, to 쓰기

        print("%s 다운로드 완료\n" % item['title'])
        # exit(-99)
        break

    with open('config.json', 'w+') as f:
        json.dump(config, f)

    # elapsed time check
    t = time.process_time() - t
    print(t)