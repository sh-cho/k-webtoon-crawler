import json
import re
import requests
import urllib.request
from bs4 import BeautifulSoup, Tag

NAVER_WEBTOON = {
    "FINISH_URL": "https://comic.naver.com/webtoon/finish.nhn",
    "LIST_URL": "https://comic.naver.com/webtoon/list.nhn?titleId=%s",
    "DETAIL_URL": "https://comic.naver.com/webtoon/detail.nhn?titleId=%s&no=%s"
}

###############################################################################################
if __name__ == "__main__":
    # 설정
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except IOError:
        config = {}

    # urllib header
    opener = urllib.request.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    urllib.request.install_opener(opener)

    # 완결웹툰
    finish_webtoon_url = NAVER_WEBTOON["FINISH_URL"]
    soup = BeautifulSoup(requests.get(finish_webtoon_url).text, 'lxml')

    download_queue = []
    soup = soup.find('body') \
        .find('div', {'id': 'wrap'}, recursive=False) \
        .find('div', {'id': 'container'}, recursive=False) \
        .find('div', {'id': 'content', 'class': 'webtoon'}, recursive=False) \
        .find('div', {'class': 'list_area'}, recursive=False) \
        .find('ul', {'class': 'img_list'}, recursive=False)

    regex = re.compile(r'\d+')
    webtoon_list = soup.find_all('li')
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

    for item in download_queue:
        # 마지막화 인덱스 구하기
        list_url = NAVER_WEBTOON["LIST_URL"] % item["titleId"]
        soup = BeautifulSoup(requests.get(list_url).text, 'lxml')
        soup = soup.find_all('td', class_='title')
        last_index = int(re.findall(r'\d+', soup[0].find('a')['href'])[1])

        episode_index = 1
        while True:
            if episode_index > last_index:    # 마지막화 체크
                break
            detail_url = NAVER_WEBTOON["DETAIL_URL"] % (item['titleId'], episode_index)
            # download
            soup = BeautifulSoup(requests.get(detail_url).text, 'lxml')
            soup = soup.find('div', class_='wt_viewer')\
                .find_all('img', {}, recursive=False)
            image_index = 1
            for img in soup:
                # TODO: 확장자 구하기
                print(img['src'])
                urllib.request.urlretrieve(img['src'], "%s_%03d_%03d.jpg" % (item['title'], episode_index, image_index))
                image_index += 1
            episode_index += 1
            exit(315)
        # TODO: config에 from, to 쓰기
        exit(-99)

    with open('config.json', 'w+') as f:
        json.dump(config, f)

