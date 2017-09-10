# pip install list
# requests, beautifulsoup4, lxml

import requests
from bs4 import BeautifulSoup, Tag

NAVER_WEBTOON_FINISH_URL = "http://comic.naver.com/webtoon/finish.nhn"

def is_stored(tag):
    #
    return isinstance(tag, Tag)

def finish_test():
    url = NAVER_WEBTOON_FINISH_URL
    source_code = requests.get(url)
    plain_text = source_code.text
    soup = BeautifulSoup(plain_text, 'lxml')
    # print(soup.prettify())
    # print(soup)

    stored_comic = []
    test = 1
    soup = soup.find('body')\
        .find('div', {'id': 'wrap'}, recursive=False)\
        .find('div', {'id': 'container'}, recursive=False)\
        .find('div', {'id': 'content', 'class': 'webtoon'}, recursive=False)\
        .find('div', {'class': 'list_area'}, recursive=False)\
        .find('ul', {'class': 'img_list'}, recursive=False)

    # test = soup.find_all(is_stored)
    lilist = soup.find_all('li')
    for tmp in lilist:
        em = tmp.find('em',class_="ico_store")
        if em is not None:
            print( tmp.find('a')['title'] )

    exit(-1)
    for child in soup:
        print("===\nchild: ", child)
        print(type(child))


    # print(soup)
    # print("====")
    print(test)
    # print(type(test))
    pass

if __name__ == "__main__":
    finish_test()
    #