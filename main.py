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

###############################################################################################
if __name__ == "__main__":
    t = time.process_time()

    try:
        with open('config.json', 'r', encoding='UTF8') as f:
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


    # 한 작품씩 다운로드 시작
    for item in download_queue:
        # 작품 별 폴더 만들기
        title_dir = (download_dir / item['title'])
        title_dir.mkdir(exist_ok=True)

        # 마지막화 인덱스 구하기
        list_url = NAVER_WEBTOON["LIST_URL"] % item["titleId"]
        soup = BeautifulSoup(requests.get(list_url).text, 'lxml')
        latest = soup.find('td', class_='title')
        last_index = int(regex.findall(latest.find('a')['href'])[1])


        # 이미 전부 다 다운받은거면 skip
        # 받고 나서 화 추가된 거 episode_index 설정
        if item['titleId'] in config['comics'] and config['comics'][item['titleId']]['last_index'] >= last_index:
            if config['comics'][item['titleId']]['last_index'] >= last_index:
                continue
            else:
                episode_index = config['comics'][item['titleId']]['last_index'] + 1
        else:
            episode_index = 1

        while True:
            if episode_index > last_index:    # 마지막화까지 받은 경우 다음 만화로 넘어가기
                break

            # TODO: 1화부터 시작하지 않고 넘어갈 경우 체크
            # TODO: 로컬에 이미 받은 파일 있는 경우(&& size!=0인 경우) 스킵

            detail_url = NAVER_WEBTOON["DETAIL_URL"] % (item['titleId'], episode_index)

            # 이미지
            image_list = []
            full_width, full_height = 0, 0

            # download
            soup = BeautifulSoup(requests.get(detail_url).text, 'lxml')
            soup = soup.select('.wt_viewer img')

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

            print("[%s] %04d / %04d" % (item['title'], episode_index, last_index))
            episode_index += 1
            # exit(315)

        # config 업데이트
        if item['titleId'] not in config['comics']:
            config['comics'][item['titleId']] = {'title': item['title']}
        config['comics'][item['titleId']]['last_index'] = last_index

        print("--- [%s] download completed ---" % item['title'])
        break

    with open('config.json', 'w+', encoding='UTF8') as f:
        json.dump(config, f, ensure_ascii=False)

    # elapsed time check
    t = time.process_time() - t
    print("%04d second(s) elapsed" % t)