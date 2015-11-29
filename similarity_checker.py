from utils import get_logger
from elasticsearch.helpers import bulk
import uuid
import traceback


def pre_process_urls(urls):
    return [url.strip() for url in urls]


class CosineSimilarity(object):
    def __init__(self, content_getter, es_client):
        self.content_getter = content_getter
        self.es_client = es_client
        self.logger = get_logger(self.__class__.__name__)
        self.index_name = 'web'
        self.doc_type = 'page'

    def create_index(self):
        # create new index
        self.index_name = str(uuid.uuid1())
        index_body = {
            'settings': {
                'number_of_shards': 1,
                'number_of_replicas': 0

            },
            'mappings': {
                self.doc_type: {
                    'properties': {
                        'content': {
                            'type': 'string',
                            'analyzer': 'standard'
                        },
                        'url': {
                            'type': 'string',
                            'index': 'not_analyzed'
                        }
                    }
                }
            }
        }

        result = self.es_client.indices.create(index=self.index_name, body=index_body)
        self.logger.info('Create index %s: %s' % (self.index_name, result))

    def index_pages(self, pages):
        actions = []
        for url, page in pages.items():
            if not page['content'] or page['error']:
                # ignore empty page or error page
                continue
            source = {
                'content': page['content'],
                'url': url
            }
            op_dict = {
                '_op_type': 'index',
                '_index': self.index_name,
                '_type': self.doc_type,
                '_source': source
            }
            actions.append(op_dict)

        success, failed = bulk(client=self.es_client, actions=actions, refresh=True, stats_only=True)
        self.logger.info('Index pages success: %d, failed: %d', success, failed)

    def delete_index(self):
        if self.es_client.indices.exists(index=self.index_name):
            result = self.es_client.indices.delete(index=self.index_name)
            self.logger.info('Delete index %s: %s' % (self.index_name, result))

    def process(self, main_url, sub_urls):
        result = []
        # pre process urls
        sub_urls = pre_process_urls(sub_urls)
        main_url = pre_process_urls([main_url])[0]
        urls = [main_url] + sub_urls
        # crawl and extract page content
        pages = self.content_getter.process(urls)
        # check similarity
        try:
            self.create_index()
            self.index_pages(pages)
            result = self.similarity(pages[main_url]['content'], main_url, sub_urls)
            self.delete_index()
        except Exception as ex:
            tb = traceback.format_exc()
            self.logger.error('Elasticsearch error (%s): %s' % (ex, tb))
            self.delete_index()

        # append error page
        del pages[main_url]
        sim_pages = {p[0] for p in result}
        for url, page in pages.items():
            if page['error']:
                result.append([url, page['error']])
                continue
            if not page['content']:
                result.append([url, 'Page not found'])
                continue
            if url not in sim_pages:
                result.append([url, 0])

        return result

    def similarity(self, content, main_url, sub_urls):
        result = []
        query = {
            'query': {
                'match': {
                    'content': content
                }
            }
        }

        hits = self.es_client.search(index=self.index_name, doc_type=self.doc_type, body=query)

        max_score = hits['hits']['max_score']

        sub_urls = set(sub_urls)
        for hit in hits['hits']['hits']:
            source = hit['_source']
            if source['url'] not in sub_urls:
                continue

            else:
                score = round(float(hit['_score'] / max_score) * 100, 2)
                result.append([source['url'], score])

        self.logger.info('Similarity info: %s' % result)
        return result

