import os
import unittest
from pprint import pprint

import requests

from parser.crawler_cluster import PageCrawlerCluster


class CrawlerClusterTestCase(unittest.TestCase):

    def test_crawling_page_using_cluster(self):
        headers = {
            'Access-Key': os.environ['CRAWLER_ACCESS_KEY']
        }
        url = 'https://edition.cnn.com/2018/07/17/politics/obama-mandela-day-address-intl/index.html'
        cluster = os.environ['CRAWLER_URL']
        response = requests.get(cluster, params={'url': url,
                                                 'pageLoadTimeout': 10,
                                                 'userAgent': 'ClarityBot',
                                                 'waitAfterLastRequest': 0.5}, headers=headers)
        # print(urllib.quote(url))
        print(response.ok)
        if not response.ok:
            print(response.reason)
        else:
            print(response.json())

    def test_crawler_cluster(self):
        crawler = PageCrawlerCluster()
        result = crawler.process(
            urls=['https://edition.cnn.com/2018/07/17/politics/obama-mandela-day-address-intl/index.html'])

        pprint(result.json())


if __name__ == '__main__':
    unittest.main()
