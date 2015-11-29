from dragnet import content_comments_extractor
from utils import get_logger


class DragnetPageExtractor(object):

    def __init__(self):
        self.logger = get_logger(__name__)

    def process(self, raw_content):
        result = raw_content
        try:
            result = content_comments_extractor.analyze(raw_content)
        except Exception as ex:
            self.logger.error('extract_page_content error: %s' % ex)

        return result
