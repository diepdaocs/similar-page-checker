import json
import os
from datetime import datetime
from multiprocessing import cpu_count
from multiprocessing.dummy import Pool

import requests
from redis import StrictRedis
from timeout_decorator import timeout, TimeoutError

from util.utils import get_logger, get_unicode


class PageCrawlerCluster(object):

    def __init__(self, user_agent='ClarityBot', page_load_timeout=15, wait_after_last_request=0.5):
        self.logger = get_logger(self.__class__.__name__)
        self.user_agent = user_agent
        self.redis = None
        self.expire_time = None
        self.cluster = os.environ.get('CRAWLER_URL', 'http://174.138.126.116:3000/execute')
        self.access_key = os.environ.get('CRAWLER_ACCESS_KEY', 'cHVwcmVuZGVyX3Nlb2NsYXJpdHk=')
        self.page_load_timeout = page_load_timeout
        self.wait_after_last_request = wait_after_last_request

    def active_redis_cache(self, expire_time):
        self.logger.info('Cache is enabled')
        self.expire_time = expire_time
        if self.redis is None:
            self.redis = StrictRedis(
                db=3, host=os.environ.get('REDIS_HOST', 'localhost'), port=os.environ.get('REDIS_PORT', 6379))

    def process(self, urls):
        result = {}
        urls = list(set(urls))

        if self.redis:
            # Get crawled pages
            for url in urls:
                page = self.redis.get(url)
                if not page:
                    continue
                self.logger.debug('Url was crawled: %s', url)
                result[url] = json.loads(get_unicode(page))

            self.logger.info("Num of crawled urls: %s" % len(result))
            # filter crawled page
            urls = [u for u in urls if u not in result]

            self.logger.info("Remain haven't crawled urls: %s" % len(urls))

            if not urls:
                self.logger.info('All urls has been crawled')
                return result

        # Crawl new urls
        if len(urls) > 2:
            # use multi thread to crawl pages
            pool = Pool(cpu_count() * 2)
            pool_results = pool.map(self._crawl_page, urls)
            # get results
            for r in pool_results:
                result.update(r)

            pool.terminate()
        else:
            for url in urls:
                result.update(self._crawl_page(url))

        if self.redis:
            # Cache result
            for url in urls:
                page = result[url]
                page['crawled_date'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                self.redis.set(url, json.dumps(page, ensure_ascii=False, encoding='utf-8'), ex=self.expire_time)

        return result

    # @timeout(15, use_signals=False)
    def _get_page(self, url):
        headers = {'Access-Key': self.access_key}
        params = {'url': url,
                  'userAgent': self.user_agent,
                  'pageLoadTimeout': self.page_load_timeout,
                  'waitAfterLastRequest': self.wait_after_last_request}
        return requests.get(self.cluster, params=params, headers=headers)

    def _crawl_page(self, url):
        self.logger.debug('Start crawl %s...' % url)
        result = {
            url: {
                'content': '',
                'error': False
            }
        }
        if url:
            try:
                response = self._get_page(url)
                # raise exception when something error
                if response.ok:
                    payload = response.json()
                    if not payload['pageTimeoutFlag']:
                        result[url]['content'] = payload['html']
                    else:
                        result[url]['error'] = 'Crawling error: %s' % 'pageTimeoutFlag=true'

                else:
                    result[url]['error'] = 'Crawling error: %s' % response.reason

                result[url]['code'] = response.status_code
                result[url]['ok'] = response.ok and not result[url]['error']

            except Exception as ex:
                self.logger.error('crawl_page error: %s' % ex.message)
                if isinstance(ex, TimeoutError):
                    result[url]['error'] = "Web page read timeout"
                else:
                    result[url]['error'] = str(ex.message)

                result[url]['code'] = 408
                result[url]['ok'] = False
        else:
            result[url]['error'] = 'url is empty'

        self.logger.debug('End crawl %s...' % url)
        return result
