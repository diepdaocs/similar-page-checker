from utils import get_logger


class ContentGetter(object):

    def __init__(self, crawler, extractor):
        self.crawler = crawler
        self.extractor = extractor
        self.logger = get_logger(self.__class__.__name__)

    def process(self, urls):
        # crawl pages
        self.logger.info('Start crawl urls: %s' % urls)
        result = self.crawler.process(urls)
        self.logger.info('End crawl urls: %s' % urls)
        # extract content from pages
        self.logger.info('Start extract pages: %s' % urls)
        for url, page in result.items():
            page['content'] = self.extractor.process(page['content'])

        self.logger.info('End extract pages: %s' % urls)
        return result
