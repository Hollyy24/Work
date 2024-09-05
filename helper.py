import requests
from  opencc import  OpenCC
from bs4 import BeautifulSoup


# search
class Bookinfo():
    def __init__(self, ISBN):
        self.BOOK_ISBN = ISBN
        self.info_list = {}
        self.cc = OpenCC('s2tw')
    def book_info(self):
        BOOK_URL = f'https://www.googleapis.com/books/v1/volumes?q=isbn:{self.BOOK_ISBN}'

        responsed = requests.get(BOOK_URL)
        if responsed.status_code == 200:
            info = responsed.json()
            if "items" in info:
                link = info['items'][0]['volumeInfo']['infoLink']
                self.scrape_bookinfo(link)
            else:
                pass
        else:
            pass
    def scrape_bookinfo(self, link):

        web = requests.get(link)
        soup = BeautifulSoup(web.text, "html.parser")

        content_label = soup.find_all('td', class_='metadata_label')
        content_value = soup.find_all('td', class_='metadata_value')
        for i in range(len(content_value)):
            self.info_list[self.cc.convert(content_label[i].text.strip())]=self.cc.convert(content_value[i].text.strip())


