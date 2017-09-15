import requests
from bs4 import BeautifulSoup, Tag
import firebase_admin
from firebase_admin import credentials, db

NAVER_WEBTOON_FINISH_URL = "http://comic.naver.com/webtoon/finish.nhn"
FIREBASE_ADMIN_ACCOUNT_KEY_PATH = "webtoon-crawler-firebase-adminsdk-zrgs2-dc46d4b66c.json"
FIREBASE_DATABASE_URL = "https://webtoon-crawler.firebaseio.com/"

if __name__ == "__main__":
    cred = credentials.Certificate(FIREBASE_ADMIN_ACCOUNT_KEY_PATH)
    firebase_admin.initialize_app(cred, {
        'databaseURL': FIREBASE_DATABASE_URL
    })
    # print(firebase_admin.db.reference().get())
    # print(type(firebase_admin.db.reference().get()))
    naver = firebase_admin.db.reference("/webtoon-list").child("naver")
    # gui = firebase_admin.db.reference("/webtoon-list/naver/여중생A")
    # gui.update({'end-no':2})

    for key, value in naver.get().items():
        webtoon = firebase_admin.db.reference("/webtoon-list/naver").child(key)
        print(webtoon.get())
    # print(naver)
    exit(-1)


    url = NAVER_WEBTOON_FINISH_URL
    source_code = requests.get(url)
    plain_text = source_code.text
    soup = BeautifulSoup(plain_text, 'lxml')
    # print(soup.prettify())
    # print(soup)

    stored_comic = []
    test = 1
    soup = soup.find('body') \
        .find('div', {'id': 'wrap'}, recursive=False) \
        .find('div', {'id': 'container'}, recursive=False) \
        .find('div', {'id': 'content', 'class': 'webtoon'}, recursive=False) \
        .find('div', {'class': 'list_area'}, recursive=False) \
        .find('ul', {'class': 'img_list'}, recursive=False)

    # test = soup.find_all(is_stored)
    lilist = soup.find_all('li')
    for tmp in lilist:
        em = tmp.find('em', class_="ico_store")
        if em is not None:
            print(tmp.find('a')['title'])

    exit(-1)
    for child in soup:
        print("===\nchild: ", child)
        print(type(child))

    # print(soup)
    # print("====")
    print(test)
    # print(type(test))
    pass