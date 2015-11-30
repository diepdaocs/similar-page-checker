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
            "http://vnexpress.net/tin-tuc/the-gioi/cuoc-song-do-day/chu-quan-cafe-tho-nhi-ky-tang-tien-cho-gia-dinh-phi-cong-nga-3319891.html",
            "http://thethao.thanhnien.com.vn/bong-da-viet-nam/o-singapore-co-dot-duoc-cung-khong-tim-thay-mot-cau-thu-nhu-cong-phuong-55893.html",
            "http://thethao.thanhnien.com.vn/bong-da-quoc-te/neymar-messi-va-ronaldo-vao-danh-sach-rut-gon-tranh-qua-bong-vang-fifa-2015-55903.html",
            "http://thethao.thanhnien.com.vn/bong-da-quoc-te/arsenal-bi-chan-thuong-tan-pha-gan-het-doi-hinh-chinh-55899.html",
            "http://edition.cnn.com/2015/11/30/opinions/sutter-obama-climate-change-cop21-two-degrees/index.html",
            "http://stackoverflow.com/questions/17555218/python-how-to-sort-a-list-of-lists-by-the-fourth-element-in-each-list"
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
            'distance_metric': 'cosine',
            'main_url': self.main_url,
            'sub_urls': ', '.join(self.sub_urls)
        }
        response = requests.post('http://localhost:8888/similarity_checker/', data=params)
        pprint(response.json())

    def test_similarity_function(self):
        from similarity_checker import cosine_similarity, jaccard_similarity, fuzzy_similarity
        tokens_1 = 'This is a foo bar sentence'.split()
        tokens_2 = 'This sentence is similar to a foo bar sentence'.split()
        pprint('jaccard: %s' % jaccard_similarity(tokens_1, tokens_2))
        pprint('cosine: %s' % cosine_similarity(tokens_1, tokens_2))
        pprint('fuzzy: %s' % fuzzy_similarity(tokens_1, tokens_2))

if __name__ == '__main__':
    unittest.main()
