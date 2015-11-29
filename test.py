import unittest
from crawler import PageCrawler
from extractor import DragnetPageExtractor
from content_getter import ContentGetter
from similarity_checker import CosineSimilarity
from utils import logger_level, INFO, DEBUG
from elasticsearch import Elasticsearch
from pprint import pprint


class MyTestCase(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(MyTestCase, self).__init__(*args, **kwargs)
        self.main_url = "http://vnexpress.net/tin-tuc/the-gioi/phan-tich/vi-sao-tho-nhi-ky-quyet-khong-xin-loi-nga-3319565.html"
        self.sub_urls = [
            "http://vnexpress.net/tin-tuc/the-gioi/tu-lieu/chuyen-xuat-kich-cuoi-cung-cua-chiec-su-24-nga-bi-ban-ha-3319680.html",
            "http://vnexpress.net/tin-tuc/the-gioi/putin-ky-sac-lenh-trung-phat-kinh-te-tho-nhi-ky-3319764.html",
            "http://vnexpress.net/tin-tuc/the-gioi/phan-tich/moi-lam-an-dang-ngo-giua-is-va-tho-nhi-ky-3319690.html",
            "http://vnexpress.net/tin-tuc/the-gioi/cuoc-song-do-day/nhat-ky-cua-mot-chien-binh-is-3319079.html",
            "http://vnexpress.net/tin-tuc/the-gioi/putin-huy-dong-tong-luc-doi-pho-moi-de-doa-tu-tho-nhi-ky-3319731.html",
            "http://vnexpress.net/tin-tuc/the-gioi/phan-tich/my-hut-hoi-truoc-ky-thuat-che-tao-bom-cua-is-3317427.html",
            "http://vnexpress.net/tin-tuc/the-gioi/phan-tich/vi-sao-tho-nhi-ky-quyet-khong-xin-loi-nga-3319565.html",
            "http://vnexpress.net/tin-tuc/thoi-su/chinh-sach-moi-co-hieu-luc-tu-thang-12-3319900.html",
            "http://vnexpress.net/tin-tuc/thoi-su/canh-sat-co-dong-bi-dam-trong-thuong-khi-chong-dua-xe-3319658.html",
            "http://vnexpress.net/tin-tuc/thoi-su/oto-tai-dam-xe-cong-nong-5-nguoi-tu-vong-3319396.html",
            "http://vnexpress.net/tin-tuc/the-gioi/cuoc-song-do-day/chu-quan-cafe-tho-nhi-ky-tang-tien-cho-gia-dinh-phi-cong-nga-3319891.html"
        ]

        logger_level = DEBUG

        self.urls = self.sub_urls + [self.main_url]
        self.crawler = PageCrawler()
        self.extractor = DragnetPageExtractor()
        self.content_getter = ContentGetter(self.crawler, self.extractor)
        self.es_client = Elasticsearch()

    def test_crawler(self):
        result = self.crawler.process(self.urls)
        pprint(result)

    def test_extractor(self):
        result = self.crawler.process(self.urls)
        for r in result.values():
            pprint(self.extractor.process(r['content']))

    def test_content_getter(self):
        result = self.content_getter.process(self.urls)
        pprint(result)

    def test_cosine_similarity(self):
        similarity = CosineSimilarity(self.content_getter, self.es_client)
        result = similarity.process(self.main_url, self.sub_urls)
        pprint(result)

    def test_api(self):
        import requests
        params = {
            'main_url': self.main_url,
            'sub_urls': self.sub_urls
        }
        response = requests.get('http://127.0.0.1:5000/api/similarity_checker', json=params)
        pprint(response.json())

if __name__ == '__main__':
    unittest.main()
