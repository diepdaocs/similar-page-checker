#!flask/bin/python

from flask import request, Flask, jsonify
from crawler import PageCrawler
from extractor import DragnetPageExtractor
from content_getter import ContentGetter
from similarity_checker import CosineSimilarity, SimilarityChecker, jaccard_similarity, cosine_similarity, \
    fuzzy_similarity, simhash_similarity, tokenize_and_normalize_content
from utils import logger_level, INFO, DEBUG
from elasticsearch import Elasticsearch
from flask_restplus import Api, Resource, fields

app = Flask(__name__)
api = Api(app, doc='/doc/', version='1.0', title='Web pages similarity')

logger_level = DEBUG

es_client = Elasticsearch()
crawler = PageCrawler()
extractor = DragnetPageExtractor()
content_getter = ContentGetter(crawler=crawler, extractor=extractor)
similarity_checker = SimilarityChecker(content_getter=content_getter, similarity=jaccard_similarity)


sim_check_params = api.model('sim_check_params', {
    'main_url': fields.String(default='http://edition.cnn.com/2015/11/29/europe/syria-turkey-russia-warplane/index.html'),
    'sub_urls': fields.String(default=["http://edition.cnn.com/2015/11/27/opinions/cagaptay-turkey-russia-tensions/index.html?iid=ob_lockedrail_topeditorial&iref=obinsite",
                                     "http://edition.cnn.com/videos/world/2015/11/28/turkey-russia-tension-dougherty-cnni-nr-lklv.cnn?iid=ob_lockedrail_topeditorial&iref=obinsite",
                                     "http://edition.cnn.com/2015/02/10/europe/ukraine-war-how-we-got-here/index.html",
                                     "http://edition.cnn.com/2015/11/19/asia/north-south-korea-talks/index.html"])
})

sim_check_response = api.model('sim_check_response', {
    'error': fields.String(default='False (boolean) if request successfully, else return error message (string)'),
    'similarity': fields.String(default="""[[url1, matching_percentage1], [url2, matching_percentage2], [url3, matching_percentage3], [url4, "Page not found]"], [url4, "Page not found]"],...]""")
})

ns1 = api.namespace('similarity_checker', 'Similarity Checker')

distance_metrics = ['jaccard', 'cosine', 'fuzzy', 'simhash']


@ns1.route('/')
class SimilarityCheckerResource(Resource):
    """Checking similarity between main web page and other web pages"""
    @api.doc(params={'distance_metric': 'Distance metric to be used (currently support %s)'
                                        % ', '.join(distance_metrics),
                     'main_url': 'Main url for checking similarity',
                     'sub_urls': 'Sub urls to be checked (urls are separated by comma)',
                     'unit': 'Unit of ngram, support value are word or character, default is word',
                     'min_ngram': 'Minimum length of ngram elements, default is 1 (minimum is 1)',
                     'max_ngram': 'Maximum length of ngram elements, default is 1 (maximum is 20)'})
    @api.response(200, 'Success', model=sim_check_response)
    def post(self):
        """Post web pages to check similarity percentage"""
        result = {
            'error': False,
            'similarity': []
        }
        # get request params
        unit = request.values.get('unit', 'word')
        min_ngram = int(request.values.get('min_ngram', 1))
        max_ngram = int(request.values.get('max_ngram', 1))
        similarity_checker.unit = unit
        similarity_checker.min_ngram = min_ngram
        similarity_checker.max_ngram                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 = max_ngram
        distance_metric = request.values.get('distance_metric', '')
        if not distance_metric or distance_metric not in distance_metrics:
            result['error'] = 'distance_metric must be in %s' % ', '.join(distance_metrics)

        elif distance_metric == 'jaccard':
            similarity_checker.similarity = jaccard_similarity

        elif distance_metric == 'cosine':
            similarity_checker.similarity = cosine_similarity

        elif distance_metric == 'fuzzy':
            similarity_checker.similarity = fuzzy_similarity

        elif distance_metric == 'simhash':
            similarity_checker.similarity = simhash_similarity

        main_url = request.values.get('main_url', '')
        sub_url_string = request.values.get('sub_urls', '')
        strip_chars = ' "\''
        sub_urls = [u.strip(strip_chars) for u in sub_url_string.split(',') if u.strip(strip_chars)]
        if not main_url:
            result['error'] = 'main_url must not blank'

        if not sub_urls:
            result['error'] = 'sub_urls must not blank'

        # validate params type
        if type(sub_urls) is not list:
            result['error'] = 'sub_urls must be in array type'

        # check similarity
        if not result['error']:
            sims = similarity_checker.process(main_url=main_url, sub_urls=sub_urls)
            if sims:
                result['similarity'] = sims
            else:
                result['error'] = 'Main page is empty'

        return jsonify(result)

    @api.doc(False)
    @api.response(200, 'Success', model=sim_check_response)
    def get(self):
        """Post web pages to check similarity percentage"""
        result = {
            'error': False,
            'similarity': []
        }
        # check request header
        if request.headers['Content-Type'] != 'application/json':
            result['error'] = 'Request params type must be application/json'
            return result

        # get request params
        params = request.get_json()
        main_url = ''
        sub_urls = []
        if 'main_url' not in params or not params['main_url'].strip():
            result['error'] = 'main_url must not blank'
        else:
            main_url = params['main_url']

        if 'sub_urls' not in params or not params['sub_urls']:
            result['error'] = 'sub_urls must not blank'
        else:
            sub_urls = params['sub_urls']

        # validate params type
        if type(sub_urls) is not list:
            result['error'] = 'sub_urls must be in array type'

        if not result['error']:
            # check similarity
            sims = similarity_checker.process(main_url=main_url, sub_urls=sub_urls)
            if sims:
                result['similarity'] = sims
            else:
                result['error'] = 'Main page is empty'

        return jsonify(result)


page_extractor_response = api.model('page_extractor_response', {
    'error': fields.String(default='False (boolean) if request successfully, else return error message (string)'),
    'pages': fields.String(default=[
        [
            'url1',
            {
                'content': 'content1',
                'tokens': 'tokens of content after tokenize',
                'error': ''
            }
        ],
        [
            'url2',
            {
                'content': 'content2',
                'tokens': 'tokens of content after tokenize',
                'error': ''
            }
        ],
        [
            'url3',
            {
                'content': 'content3',
                'tokens': 'tokens of content after tokenize',
                'error': ''
            }
        ]
    ])
})

ns2 = api.namespace('page_extractor', 'Page Extractor')


@ns2.route('/extractor')
class PageExtractorResource(Resource):
    """Extract content from crawled web pages"""
    @api.doc(params={'urls': 'The urls to be extracted content (If many urls, separate by comma)',
                     'unit': 'Unit of ngram, support value are word or character, default is word',
                     'min_ngram': 'Minimum length of ngram elements, default is 1 (minimum is 1)',
                     'max_ngram': 'Maximum length of ngram elements, default is 1 (maximum is 20)'})
    @api.response(200, 'Success', model='page_extractor_response')
    def get(self):
        """Post web pages to extract content"""
        result = {
            'error': False,
            'pages': []
        }
        unit = request.values.get('unit', 'word')
        min_ngram = int(request.values.get('min_ngram', 1))
        max_ngram = int(request.values.get('max_ngram', 1))
        urls = request.values.get('urls', '')
        strip_chars = ' "\''
        urls = [u.strip(strip_chars) for u in urls.split(',') if u.strip(strip_chars)]
        if not urls:
            result['error'] = 'urls must not be empty'
        if not result['error']:
            pages = result['pages']
            for url, page in content_getter.process(urls).items():
                page['tokens'] = tokenize_and_normalize_content(page['content'], unit=unit, min_ngram=min_ngram,
                                                                max_ngram=max_ngram)
                pages.append((url, page))

        return jsonify(result)


content_sim_response = api.model('content_sim_response', {
    'error': fields.String(default='False (boolean) if request successfully, else return error message (string)'),
    'tokens_1': fields.String(default='Tokens of content_1 after tokenize'),
    'tokens_2': fields.String(default='Tokens of content_2 after tokenize'),
    'distances': fields.String(default=[
        [
            {
                'metric1': 'matching percentage'
            }
        ],
        [
            {
                'metric2': 'matching percentage'
            }
        ],
        [
            {
                'metric3': 'matching percentage'
            }
        ],
    ])
})


ns3 = api.namespace('content', 'Content Similarity')


def get_similarity_checker(name):
    result = None
    if name == 'jaccard':
        result = jaccard_similarity

    elif name == 'cosine':
        result = cosine_similarity

    elif name == 'fuzzy':
        result = fuzzy_similarity

    elif name == 'simhash':
        result = simhash_similarity
    return result


@ns3.route('/similarity')
class ContentSimilarityResource(Resource):
    """Check similarity between content"""
    from collections import OrderedDict
    @api.doc(params=OrderedDict({'content_1': 'Content to be checked', 'content_2': 'Another content to be checked',
                     'distance_metrics': 'Distance metrics to be used (currently support %s), if empty, show all '
                                         'distance metrics result, if many, separate by comma.'
                                         % ', '.join(distance_metrics),
                     'unit': 'Unit of ngram, support value are word or character, default is word',
                     'min_ngram': 'Minimum length of ngram elements, default is 1 (minimum is 1)',
                     'max_ngram': 'Maximum length of ngram elements, default is 1 (maximum is 20)'}))
    @api.response(200, 'Success', model='content_sim_response')
    def get(self):
        """Post content to check similarity"""
        result = {
            'error': False,
            'distances': [],
            'tokens_1': [],
            'tokens_2': []
        }
        unit = request.values.get('unit', 'word')
        min_ngram = int(request.values.get('min_ngram', 1))
        max_ngram = int(request.values.get('max_ngram', 1))
        content_1 = tokenize_and_normalize_content(request.values.get('content_1', ''), unit=unit, min_ngram=min_ngram,
                                                   max_ngram=max_ngram)
        content_2 = tokenize_and_normalize_content(request.values.get('content_2', ''), unit=unit, min_ngram=min_ngram,
                                                   max_ngram=max_ngram)
        result['tokens_1'] = content_1
        result['tokens_2'] = content_2
        selected_dm = request.values.get('distance_metrics', '')
        strip_chars = ' "\''
        selected_dm = [d.strip(strip_chars).lower() for d in selected_dm.split(',') if d.strip(strip_chars)]
        if not selected_dm:
            selected_dm = distance_metrics

        distances = result['distances']
        for dm_name in selected_dm:
            sim_checker = get_similarity_checker(dm_name)
            if sim_checker:
                distances.append({dm_name: sim_checker(content_1, content_2)})
            else:
                distances.append({dm_name: 'Distance metric %s do not existed, we support only %s' %
                                           (dm_name, ', '.join(distance_metrics))})

        return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True, host='107.170.109.238', port=8888)
    # app.run(debug=True, port=8888)
