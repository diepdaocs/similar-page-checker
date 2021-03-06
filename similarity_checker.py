import math
from fuzzywuzzy import fuzz
from nltk.stem.porter import PorterStemmer

from util.utils import get_logger
from elasticsearch.helpers import bulk
import uuid
import traceback
from nltk.tokenize.toktok import ToktokTokenizer
from nltk.util import ngrams
import string
from simhash import Simhash


tokenize = ToktokTokenizer().tokenize
stemmer = PorterStemmer()


def pre_process_urls(urls):
    return [url.strip() for url in urls]


def tokenize_and_normalize_content(content, unit='word', min_ngram=1, max_ngram=1):
    # pre check condition
    if max_ngram < 1:
        max_ngram = 1
    if max_ngram > 20:
        max_ngram = 20
    if min_ngram < 1:
        min_ngram = 1
    if max_ngram < min_ngram:
        max_ngram = min_ngram
    if unit not in ['word', 'character']:
        unit = 'word'

    if type(content) is not unicode:
        content = unicode(content, 'utf-8', errors='ignore')

    result = []

    # pre tokenize
    words = []
    for word in tokenize(content):
        word = normalize(word)
        if not word:
            continue
        words.append(word)

    # generate ngram
    if unit == 'character':
        words = ''.join(words)

    for n in range(min_ngram, max_ngram + 1):
        cols = ngrams(words, n)
        for e in cols:
            if unit == 'word':
                result.append(' '.join(e))
            else:
                result.append(''.join(e))

    return result


def normalize(word):
    return stemmer.stem(word.strip(string.punctuation).lower())


def cosine_similarity(tokens_1, tokens_2):
    vec_1 = {w: 1 for w in tokens_1}
    vec_2 = {w: 1 for w in tokens_2}
    intersection = set(vec_1.keys()) & set(vec_2.keys())
    numerator = sum([vec_1[x] * vec_2[x] for x in intersection])
    sum_1 = sum([vec_1[x]**2 for x in vec_1.keys()])
    sum_2 = sum([vec_2[x]**2 for x in vec_2.keys()])
    denominator = math.sqrt(sum_1) * math.sqrt(sum_2)

    if not denominator:
        return 0.0
    else:
        return round(float(numerator) / denominator * 100, 2)


def jaccard_similarity(tokens_1, tokens_2):
    tokens_1 = set(tokens_1)
    tokens_2 = set(tokens_2)
    union = len(tokens_1 | tokens_2)
    if not union:
        return 0.0

    return round(float(len(tokens_1 & tokens_2)) / union * 100, 2)


def fuzzy_similarity(tokens_1, tokens_2):
    return fuzz.token_sort_ratio(' '.join(tokens_1), ' '.join(tokens_2))


def simhash_similarity(tokens_1, tokens_2):
    if not tokens_1 or not tokens_2:
        return 0
    return 100 - Simhash(tokens_1).distance(Simhash(tokens_2))


class SimilarityChecker(object):
    def __init__(self, content_getter, similarity, unit='word', min_ngram=1, max_ngram=1, main_page_selector=None,
                 sub_page_selector=None, url_1_selector=None, url_2_selector=None, url_3_selector=None):
        self.similarity = similarity
        self.content_getter = content_getter
        self.main_page_selector = main_page_selector
        self.sub_page_selector = sub_page_selector
        self.url_1_selector = url_1_selector
        self.url_2_selector = url_2_selector
        self.url_3_selector = url_3_selector
        self.unit = unit
        self.min_ngram = min_ngram
        self.max_ngram = max_ngram
        self.logger = get_logger(self.__class__.__name__)

    def process(self, main_url, sub_urls):
        result = []
        # pre process urls
        sub_urls = pre_process_urls(sub_urls)
        main_url = pre_process_urls([main_url])[0]
        # crawl and extract page content
        pages = {}
        whole_content_urls = []
        if self.main_page_selector:
            self.content_getter.extractor.selector = self.main_page_selector
            pages.update(self.content_getter.process([main_url]))
        else:
            whole_content_urls.append(main_url)

        if self.sub_page_selector:
            self.content_getter.extractor.selector = self.sub_page_selector
            pages.update(self.content_getter.process(sub_urls))
        else:
            whole_content_urls.extend(sub_urls)

        if whole_content_urls:
            pages = self.content_getter.process(whole_content_urls)

        # verify main page
        main_page = pages[main_url]['content']
        if not main_page:
            result = []
            return result
        # tokenize content into words
        for url, page in pages.items():
            page['content'] = tokenize_and_normalize_content(page['content'], unit=self.unit,
                                                             min_ngram=self.min_ngram, max_ngram=self.max_ngram)

        # check similarity
        main_tokens = pages[main_url]['content']
        for url, page in pages.items():
            if url not in sub_urls:
                continue
            sub_tokens = page['content']
            if page.get('error'):
                result.append([url, 'Page not found'])
                continue

            sim = self.similarity(main_tokens, sub_tokens)
            result.append([url, sim])

        # sort result
        result.sort(key=lambda x: x[1], reverse=True)
        self.logger.debug('Similarity result: %s' % result)
        return result

    def cross_process(self, url_1, url_2, url_3):
        result = {}
        # pre process urls
        url_1 = pre_process_urls([url_1])[0]
        url_2 = pre_process_urls([url_2])[0]
        url_3 = pre_process_urls([url_3])[0]
        # crawl and extract page content
        pages = {}
        whole_content_urls = []
        if self.url_1_selector:
            self.content_getter.extractor.selector = self.url_1_selector
            pages.update(self.content_getter.process([url_1]))
        else:
            whole_content_urls.append(url_1)

        if self.url_2_selector:
            self.content_getter.extractor.selector = self.url_2_selector
            pages.update(self.content_getter.process([url_2]))
        else:
            whole_content_urls.append(url_2)

        if self.url_3_selector:
            self.content_getter.extractor.selector = self.url_3_selector
            pages.update(self.content_getter.process([url_3]))
        else:
            whole_content_urls.append(url_3)

        if whole_content_urls:
            pages = self.content_getter.process(whole_content_urls)

        # tokenize content into words
        for url, page in pages.items():
            page['content'] = tokenize_and_normalize_content(page['content'], unit=self.unit,
                                                             min_ngram=self.min_ngram, max_ngram=self.max_ngram)

        # check similarity
        result.update({
            'sim12': cal_sim(pages, url_1, url_2, self.similarity),
            'sim23': cal_sim(pages, url_2, url_3, self.similarity),
            'sim13': cal_sim(pages, url_1, url_3, self.similarity),
        })
        self.logger.debug('Similarity result: %s' % result)
        return result


def cal_sim(pages, url_1, url_2, sim_func):
    page_1 = pages[url_1]
    page_2 = pages[url_2]
    if page_1.get('error'):
        return 'Page not found: %s' % url_1
    if page_2.get('error'):
        return 'Page not found: %s' % url_2
    return sim_func(page_1['content'], page_2['content'])


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
        self.logger.debug('Create index %s: %s' % (self.index_name, result))

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
        self.logger.debug('Index pages success: %d, failed: %d', success, failed)

    def delete_index(self):
        if self.es_client.indices.exists(index=self.index_name):
            result = self.es_client.indices.delete(index=self.index_name)
            self.logger.debug('Delete index %s: %s' % (self.index_name, result))

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
            result = self.similarity(pages[main_url]['content'], sub_urls)
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

    def similarity(self, content, sub_urls):
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

        self.logger.debug('Similarity info: %s' % result)
        return result
