import unittest
from parser.crawler import PageCrawler
from parser.extractor import DragnetPageExtractor, AllTextPageExtractor, get_text_from_url
from parser.content_getter import ContentGetter
from similarity_checker import CosineSimilarity
from util.utils import logger_level, INFO, DEBUG
from elasticsearch import Elasticsearch
from pprint import pprint
from multiprocessing.dummy import Pool
import requests

import logging

logging.basicConfig()


class MyTestCase(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(MyTestCase, self).__init__(*args, **kwargs)
        self.main_url = "http://flask.pocoo.org/docs/0.10/deploying/wsgi-standalone/"
        self.sub_urls = [
            "http://flask.pocoo.org/docs/0.10/deploying/wsgi-standalone/"
        ]

        self.urls = self.sub_urls + [self.main_url]
        self.crawler = PageCrawler()
        self.extractor = DragnetPageExtractor()
        self.content_getter = ContentGetter(self.crawler, self.extractor)
        self.es_client = Elasticsearch()

    def test_crawler(self):
        result = self.crawler.process(self.urls)
        pprint(result)

    def test_extractor(self):
        pprint(self.extractor.process(self.crawler.process(self.urls)))

    def test_all_text_extractor(self):
        self.extractor = AllTextPageExtractor()
        pprint(self.extractor.process(self.crawler.process([
            'https://www.uncommongoods.com/gifts/personalized/personalized-gifts'
        ])))

    def test_all_text_extractor2(self):
        self.extractor = AllTextPageExtractor()
        pprint(self.extractor.process(self.crawler.process([
            'https://vnexpress.net/tin-tuc/thoi-su/8-nguoi-chet-hon-tram-nghin-ngoi-nha-bi-toc-mai-do-bao-doksuri-3642317.html'
        ])))

    def test_get_text_from_url(self):
        urls = ['https://www.uncommongoods.com/gifts/personalized/personalized-gifts',
                'https://stackoverflow.com/questions/1521592/get-root-domain-of-link',
                'https://docs.python.org/2/library/urlparse.html']

        for url in urls:
            print get_text_from_url(url)

    def test_content_getter(self):
        result = self.content_getter.process(self.urls)
        pprint(result)

    def test_cosine_similarity(self):
        similarity = CosineSimilarity(self.content_getter, self.es_client)
        result = similarity.process(self.main_url, self.sub_urls)
        pprint(result)

    def _call_api(self, i):
        params = {
            'distance_metric': 'cosine',
            'main_url': self.main_url,
            'sub_urls': ', '.join(self.sub_urls)
        }
        response = requests.post('http://107.170.109.238:8888/similarity/check', data=params)
        print i

    def test_api(self):
        params = {
            'distance_metric': 'cosine',
            'main_url': self.main_url,
            'sub_urls': ', '.join(self.sub_urls)
        }
        pool = Pool(4)
        pool.map(self._call_api, range(2000))

    def test_similarity_function(self):
        from similarity_checker import cosine_similarity, jaccard_similarity, fuzzy_similarity, simhash_similarity
        tokens_1 = 'This is a foo ba'.split()
        tokens_2 = 'This sentence is similar to a foo bar sentence'.split()
        pprint('jaccard: %s' % jaccard_similarity(tokens_1, tokens_2))
        pprint('cosine: %s' % cosine_similarity(tokens_1, tokens_2))
        pprint('fuzzy: %s' % fuzzy_similarity(tokens_1, tokens_2))
        pprint('simhash: %s' % simhash_similarity(tokens_1, tokens_2))

    def test_tokenizer(self):
        from similarity_checker import tokenize_and_normalize_content
        url = 'https://www.travelocity.com/Las-Vegas-Hotels-MGM-Grand-Hotel-Casino.h12628.Hotel-Information'
        page = self.content_getter.process([url])
        pprint(tokenize_and_normalize_content(page[url]['content']))

    def test_tokenize_and_normalize(self):
        from similarity_checker import tokenize_and_normalize_content
        text = 'what are you doing'
        pprint(tokenize_and_normalize_content(text, unit='character', min_ngram=1, max_ngram=3))

if __name__ == '__main__':
    unittest.main()
