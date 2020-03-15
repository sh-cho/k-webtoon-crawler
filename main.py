import io
import json
import PIL.Image
import lzstring
import re
import requests
import rsa
import time
import uuid
import unicodedata
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from pathlib import Path
from bs4 import BeautifulSoup


NAVER_WEBTOON = {
    "FINISH_URL": "https://comic.naver.com/webtoon/finish.nhn",
    "LIST_URL": "https://comic.naver.com/webtoon/list.nhn?titleId=%s",
    "DETAIL_URL": "https://comic.naver.com/webtoon/detail.nhn?titleId=%s&no=%s",
}


last_status = {}


def update_last_index(_config, _item, _last_index):
    if _item['titleId'] not in _config['comics']:
        _config['comics'][_item['titleId']] = {'title': _item['title']}
        if 'titleOriginal' in _item:    # 원 제목 있는 경우 추가
            _config['comics'][_item['titleId']]['titleOriginal'] = _item['titleOriginal']
    _config['comics'][_item['titleId']]['lastIndex'] = _last_index
    return


def dump_config_file(_config):
    with open('config.json', 'w+', encoding='UTF8') as _conf_file:
        json.dump(_config, _conf_file, ensure_ascii=False, indent=4)


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
    # key_str = requests.get('http://static.nid.naver.com/enclogin/keys.nhn').content.decode("utf-8")
    key_str = requests.get('https://nid.naver.com/login/ext/keys.nhn').content.decode("utf-8")
    return encrypt(key_str, uid, upw)


def naver_session(nid, npw):
    encnm, encpw = encrypt_account(nid, npw)

    s = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.1,
        status_forcelist=[500, 502, 503, 504]
    )
    s.mount('https://', HTTPAdapter(max_retries=retries))
    request_headers = {
        'User-agent': 'Mozilla/5.0'
    }

    # time.sleep(0.5)
    bvsd_uuid = uuid.uuid4()
    encData = '{"a":"%s-4","b":"1.3.4","d":[{"i":"id","b":{"a":["0,%s"]},"d":"%s","e":false,"f":false},{"i":"%s","e":true,"f":false}],"h":"1f","i":{"a":"Mozilla/5.0"}}' % (bvsd_uuid, nid, nid, npw)
    bvsd = '{"uuid":"%s","encData":"%s"}' % (bvsd_uuid, lzstring.LZString.compressToEncodedURIComponent(encData))

    resp = s.post('https://nid.naver.com/nidlogin.login', data={
        'svctype': '0',
        'enctp': '1',
        'encnm': encnm,
        'enc_url': 'http0X0.0000000000001P-10220.0000000.000000www.naver.com',
        'url': 'www.naver.com',
        'smart_level': '1',
        'encpw': encpw,
        'bvsd': bvsd
    }, headers=request_headers)

    finalize_url = re.search(r'location\.replace\("([^"]+)"\)', resp.content.decode("utf-8")).group(1)
    s.get(finalize_url)

    return s



###############################################################################################
if __name__ == "__main__":
    t = time.process_time()

    try:
        with open('config.json', 'r', encoding='UTF8') as f:
            config = json.load(f)
    except IOError:
        config = {"comics": {}}

    try:
        with open('naver.json', 'r') as f:
            naver_account = json.load(f)
    except IOError:
        print("naver.json 파일 설정 필요")
        exit(-1)

    # HTTP Req header
    request_headers = {
        'User-agent': 'Mozilla/5.0'
    }

    # session
    # 네이버 로그인 (19세 이상 만화 받기 위해서)
    # 너무 힘들었다ㅠ
    session = naver_session(naver_account['id'], naver_account['password'])

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
            if webtoon_info['title'] != description['title']:   # slugify로 제목 달라진 경우 원제목 추가
                webtoon_info['titleOriginal'] = description['title']
            download_queue.append(webtoon_info)

    try:
        # 한 작품씩 다운로드 시작
        for item in download_queue:
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

            # 작품 별 폴더 만들기
            title_dir = (download_dir / item['title'])
            title_dir.mkdir(exist_ok=True)

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
                    # TODO: img_data 오류날 경우 (아무것도 없을 때) -> 다시 받기
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
                # config 파일 업데이트 (매 화 받을 때마다)
                update_last_index(config, item, episode_index)
                dump_config_file(config)
                episode_index += 1

            # config 업데이트
            #update_last_index(config, item, last_index)
            last_status = {"item": item, "lastIndex": last_index}

            print("--- [%s] download completed ---" % item['title'])
            #break   # test
    except Exception as exc:
        print('*** error has occurred ***')
        print(exc)
        with open('error.log', 'w+', encoding='UTF8') as f:
            f.write(str(exc))
        update_last_index(config, last_status['item'], last_status['lastIndex'])
    finally:
        dump_config_file(config)

    # elapsed time check
    t = time.process_time() - t
    print("%04d second(s) elapsed" % t)
    # main end