from flask import request, Flask, jsonify
from parser.crawler import PageCrawler
from parser.content_getter import ContentGetter
from parser.extractor import DragnetPageExtractor, ReadabilityPageExtractor, GoosePageExtractor, \
    GooseDragnetPageExtractor, SelectivePageExtractor, AllTextPageExtractor
from similarity_checker import SimilarityChecker, jaccard_similarity, cosine_similarity, \
    fuzzy_similarity, simhash_similarity, tokenize_and_normalize_content
from flask_restplus import Api, Resource, fields
from app import app

api = Api(app, doc='/doc/', version='1.0', title='Web pages similarity')

crawler = PageCrawler()
extractor = DragnetPageExtractor()
content_getter = ContentGetter(crawler=crawler, extractor=extractor)
similarity_checker = SimilarityChecker(content_getter=content_getter, similarity=cosine_similarity)

list_extractor = ['dragnet', 'goose', 'goose_dragnet', 'readability', 'selective', 'all_text']


def get_extractor(name):
    if name == 'dragnet':
        return DragnetPageExtractor()
    elif name == 'readability':
        return ReadabilityPageExtractor()
    elif name == 'goose':
        return GoosePageExtractor()
    elif name == 'goose_dragnet':
        return GooseDragnetPageExtractor()
    elif name == 'selective':
        return SelectivePageExtractor(selector='')
    elif name == 'all_text':
        return AllTextPageExtractor()
    else:
        return None

list_selector_type = ['css', 'xpath']

sim_check_params = api.model('sim_check_params', {
    'main_url': fields.String(
        default='http://edition.cnn.com/2015/11/29/europe/syria-turkey-russia-warplane/index.html'),
    'sub_urls': fields.String(default=[
        "http://edition.cnn.com/2015/11/27/opinions/cagaptay-turkey-russia-tensions/index.html?iid=ob_lockedrail_topeditorial&iref=obinsite",
        "http://edition.cnn.com/videos/world/2015/11/28/turkey-russia-tension-dougherty-cnni-nr-lklv.cnn?iid=ob_lockedrail_topeditorial&iref=obinsite",
        "http://edition.cnn.com/2015/02/10/europe/ukraine-war-how-we-got-here/index.html",
        "http://edition.cnn.com/2015/11/19/asia/north-south-korea-talks/index.html"])
})

sim_check_response = api.model('sim_check_response', {
    'error': fields.String(default='False (boolean) if request successfully, else return error message (string)'),
    'similarity': fields.String(default="""[[url1, matching_percentage1], [url2, matching_percentage2], [url3, matching_percentage3], [url4, "Page not found]"], [url4, "Page not found]"],...]""")
})

ns1 = api.namespace('similarity', 'Similarity Checker')

distance_metrics = ['jaccard', 'cosine', 'fuzzy', 'simhash']

user_agents = ['Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) '
               'Chrome/39.0.2171.95 Safari/537.36']


@ns1.route('/check')
class SimilarityCheckerResource(Resource):
    """Checking similarity between main web page and other web pages"""
    @api.doc(params={'distance_metric': 'Distance metric to be used (currently support %s), default is `cosine`'
                                        % ', '.join(distance_metrics),
                     'main_url': 'Main url for checking similarity',
                     'sub_urls': 'Sub urls to be checked (urls are separated by comma)',
                     'unit': 'Unit of ngram, support value are word or character, default is `word`',
                     'min_ngram': 'Minimum length of ngram elements, default is 1 (minimum is 1)',
                     'max_ngram': 'Maximum length of ngram elements, default is 1 (maximum is 20)',
                     'extractor': 'The name of extractor to be used, currently support `%s`, default `%s`, '
                                  'if the extractor name is `selective`, you must specify `main_page_selector`, '
                                  '`sub_page_selector` and `selector_type` (default is `css`)' %
                                  (', '.join(list_extractor), list_extractor[0]),
                     'selector_type': 'The name of selector type to be used, currently support `%s`, default is `%s`' %
                                  (', '.join(list_selector_type), list_selector_type[0]),
                     'main_page_selector': 'Main page selector, if extractor is `selective`, '
                                           'you must specify the `main_page_selector` element',
                     'sub_page_selector': 'Sub page selector, if extractor is `selective`, '
                                          'you must specify the `sub_page_selector` element',
                     'user_agent': "The 'User-Agent' of crawler, default is `%s`" % user_agents[0]
                     }
             )
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
        similarity_checker.max_ngram = max_ngram
        distance_metric = request.values.get('distance_metric', '')
        if not distance_metric:
            similarity_checker.similarity = cosine_similarity
        elif distance_metric not in distance_metrics:
            result['error'] = 'distance_metric must be in %s' % ', '.join(distance_metrics)
            return result

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
            return result

        if not sub_urls:
            result['error'] = 'sub_urls must not blank'
            return result

        # validate params type
        if type(sub_urls) is not list:
            result['error'] = 'sub_urls must be in array type'
            return result

        extractor_name = request.values.get('extractor', list_extractor[0])
        s_extractor = get_extractor(extractor_name)
        if not extractor:
            result['error'] = "The extractor name '%s' does not support yet" % extractor_name
            return result
        main_page_selector = None
        sub_page_selector = None
        if extractor_name == 'selective':
            s_extractor.selector_type = request.values.get('selector_type', list_extractor[0])
            main_page_selector = request.values.get('main_page_selector')
            sub_page_selector = request.values.get('sub_page_selector')
            if not main_page_selector or not main_page_selector.strip():
                result['error'] = "You must specify the 'main_page_selector' element when the 'extractor' " \
                                  "is 'selective'"
                return result
            if not sub_page_selector or not sub_page_selector.strip():
                result[
                    'error'] = "You must specify the 'sub_page_selector' element when the 'extractor' is 'selective'"
                return result

        user_agent = request.values.get('user_agent', user_agents[0])
        s_content_getter = ContentGetter(crawler=PageCrawler(user_agent=user_agent.strip()), extractor=s_extractor)

        # check similarity
        if not result['error']:
            similarity_checker.content_getter = s_content_getter
            if main_page_selector:
                similarity_checker.main_page_selector = main_page_selector.strip()
                similarity_checker.sub_page_selector = sub_page_selector.strip()
            sims = similarity_checker.process(main_url=main_url, sub_urls=sub_urls)
            if sims:
                result['similarity'] = sims
            else:
                result['error'] = 'Main page is empty'

        return jsonify(result)


@ns1.route('/cross-check')
class SimilarityCrossCheckerResource(Resource):
    """Checking similarity between main web page and other web pages"""
    @api.doc(params={'distance_metric': 'Distance metric to be used (currently support %s), default is `cosine`'
                                        % ', '.join(distance_metrics),
                     'url_1': 'Url 1',
                     'url_2': 'Url 2',
                     'url_3': 'Url 3',
                     'unit': 'Unit of ngram, support value are word or character, default is `word`',
                     'min_ngram': 'Minimum length of ngram elements, default is 1 (minimum is 1)',
                     'max_ngram': 'Maximum length of ngram elements, default is 1 (maximum is 20)',
                     'extractor': 'The name of extractor to be used, currently support `%s`, default `%s`, '
                                  'if the extractor name is `selective`, you must specify `main_page_selector`, '
                                  '`sub_page_selector` and `selector_type` (default is `css`)' %
                                  (', '.join(list_extractor), list_extractor[0]),
                     'selector_type': 'The name of selector type to be used, currently support `%s`, default is `%s`' %
                                  (', '.join(list_selector_type), list_selector_type[0]),
                     'url_1_selector': 'Url 1 selector, if extractor is `selective`, '
                                       'you must specify the `url_1_selector` element',
                     'url_2_selector': 'Url 2 selector, if extractor is `selective`, '
                                       'you must specify the `url_2_selector` element',
                     'url_3_selector': 'Url 3 selector, if extractor is `selective`, '
                                       'you must specify the `url_3_selector` element',
                     'user_agent': "The 'User-Agent' of crawler, default is `%s`" % user_agents[0]
                     }
             )
    @api.response(200, 'Success')
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
        similarity_checker.max_ngram = max_ngram
        distance_metric = request.values.get('distance_metric', '')
        if not distance_metric:
            similarity_checker.similarity = cosine_similarity
        elif distance_metric not in distance_metrics:
            result['error'] = 'distance_metric must be in %s' % ', '.join(distance_metrics)
            return result

        elif distance_metric == 'jaccard':
            similarity_checker.similarity = jaccard_similarity

        elif distance_metric == 'cosine':
            similarity_checker.similarity = cosine_similarity

        elif distance_metric == 'fuzzy':
            similarity_checker.similarity = fuzzy_similarity

        elif distance_metric == 'simhash':
            similarity_checker.similarity = simhash_similarity

        url_1 = request.values.get('url_1', '')
        url_2 = request.values.get('url_2', '')
        url_3 = request.values.get('url_3', '')
        if not url_1:
            result['error'] = 'url_1 must not blank'
            return result

        if not url_2:
            result['error'] = 'url_2 must not blank'
            return result

        if not url_3:
            result['error'] = 'url_3 must not blank'
            return result

        extractor_name = request.values.get('extractor', list_extractor[0])
        s_extractor = get_extractor(extractor_name)
        if not extractor:
            result['error'] = "The extractor name '%s' does not support yet" % extractor_name
            return result
        url_1_selector = None
        url_2_selector = None
        url_3_selector = None
        if extractor_name == 'selective':
            s_extractor.selector_type = request.values.get('selector_type', list_extractor[0])
            url_1_selector = request.values.get('url_1_selector')
            url_2_selector = request.values.get('url_2_selector')
            url_3_selector = request.values.get('url_3_selector')
            if not url_1_selector or not url_1_selector.strip():
                result['error'] = "You must specify the 'url_1_selector' element when the 'extractor' " \
                                  "is 'selective'"
                return result
            if not url_2_selector or not url_2_selector.strip():
                result[
                    'error'] = "You must specify the 'url_2_selector' element when the 'extractor' is 'selective'"
                return result
            if not url_3_selector or not url_3_selector.strip():
                result[
                    'error'] = "You must specify the 'url_3_selector' element when the 'extractor' is 'selective'"
                return result

        user_agent = request.values.get('user_agent', user_agents[0])
        s_content_getter = ContentGetter(crawler=PageCrawler(user_agent=user_agent.strip()), extractor=s_extractor)

        # check similarity
        if not result['error']:
            similarity_checker.content_getter = s_content_getter
            similarity_checker.url_1_selector = url_1_selector
            similarity_checker.url_2_selector = url_2_selector
            similarity_checker.url_3_selector = url_3_selector
            sims = similarity_checker.cross_process(url_1, url_2, url_3)
            if sims:
                result['similarity'] = sims

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

ns2 = api.namespace('page', 'Page Extractor')


@ns2.route('/extract')
class PageExtractorResource(Resource):
    """Extract content from crawled web pages"""
    @api.doc(params={'urls': 'The urls to be extracted content (If many urls, separate by comma)',
                     'unit': 'Unit of ngram, support value are word or character, default is `word`',
                     'min_ngram': 'Minimum length of ngram elements, default is 1 (minimum is 1)',
                     'max_ngram': 'Maximum length of ngram elements, default is 1 (maximum is 20)',
                     'extractor': 'The name of extractor to be used, currently support `%s`, default `%s`' %
                                  (', '.join(list_extractor), list_extractor[0]),
                     'selector_type': 'The name of selector type to be used, currently support `%s`, default is `%s`, '
                                      'if the extractor name is `selective`, you must specify the '
                                      '`selector` and `selector_type` (default is `css`)' %
                                  (', '.join(list_selector_type), list_selector_type[0]),
                     'selector': 'If extractor is `selective`, you must specify the `selector` element',
                     'user_agent': "The 'User-Agent' of crawler, default is `%s`" % user_agents[0],
                     'cache': 'Cache result for later use faster (integer), `0` is cache disabled, '
                              '`others` is cache enabled. Default is non-cache',
                     'expire_time': 'Expire time for cache (second), only effect when cache enabled. '
                                    'Default is `604800` seconds (7 days)'
                     }
             )
    @api.response(200, 'Success', model='page_extractor_response')
    def post(self):
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

        extractor_name = request.values.get('extractor', list_extractor[0])
        s_extractor = get_extractor(extractor_name)
        if not extractor:
            result['error'] = "The extractor name '%s' does not support yet" % extractor_name
            return result
        if extractor_name == 'selective':
            s_extractor.selector_type = request.values.get('selector_type', list_extractor[0])
            selector = request.values.get('selector')
            if not selector or not selector.strip():
                result['error'] = "You must specify the 'selector' element when the 'extractor' is 'selective'"
                return result
            s_extractor.selector = selector.strip()

        user_agent = request.values.get('user_agent', user_agents[0])
        s_crawler = PageCrawler(user_agent=user_agent)
        cache = int(request.values.get('cache', 0))
        if cache != 0:
            expire_time = int(request.values.get('expire_time', 604800))  # Seconds = 7 days
            s_crawler.active_redis_cache(expire_time)

        s_content_getter = ContentGetter(crawler=s_crawler, extractor=s_extractor)

        if not result['error']:
            pages = result['pages']
            for url, page in s_content_getter.process(urls).items():
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
    @api.doc(params={'content_1': 'Content to be checked', 'content_2': 'Another content to be checked',
                     'distance_metrics': 'Distance metrics to be used (currently support %s), if empty, show all '
                                         'distance metrics result, if many, separate by comma.'
                                         % ', '.join(distance_metrics),
                     'unit': 'Unit of ngram, support value are `word` or `character`, default is `word`',
                     'min_ngram': 'Minimum length of ngram elements, default is 1 (minimum is 1)',
                     'max_ngram': 'Maximum length of ngram elements, default is 1 (maximum is 20)'
                     }
             )
    @api.response(200, 'Success', model='content_sim_response')
    def post(self):
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

        result['distances'] = cal_distances(content_1, content_2, selected_dm)

        return jsonify(result)


@ns3.route('/cross-similarity')
class ContentCrossSimilarityResource(Resource):
    """Check similarity between content"""
    @api.doc(params={'content_1': 'Content to be checked', 'content_2': 'Another content to be checked',
                     'content_3': 'Another content to be checked',
                     'distance_metrics': 'Distance metrics to be used (currently support %s), if empty, show all '
                                         'distance metrics result, if many, separate by comma.'
                                         % ', '.join(distance_metrics),
                     'unit': 'Unit of ngram, support value are `word` or `character`, default is `word`',
                     'min_ngram': 'Minimum length of ngram elements, default is 1 (minimum is 1)',
                     'max_ngram': 'Maximum length of ngram elements, default is 1 (maximum is 20)'
                     }
             )
    @api.response(200, 'Success')
    def post(self):
        """Post content to check similarity"""
        result = {
            'error': False,
            'distances12': [],
            'distances23': [],
            'distances13': [],
            'tokens_1': [],
            'tokens_2': [],
            'tokens_3': []
        }
        unit = request.values.get('unit', 'word')
        min_ngram = int(request.values.get('min_ngram', 1))
        max_ngram = int(request.values.get('max_ngram', 1))
        content_1 = tokenize_and_normalize_content(request.values.get('content_1', ''), unit=unit, min_ngram=min_ngram,
                                                   max_ngram=max_ngram)
        content_2 = tokenize_and_normalize_content(request.values.get('content_2', ''), unit=unit, min_ngram=min_ngram,
                                                   max_ngram=max_ngram)
        content_3 = tokenize_and_normalize_content(request.values.get('content_3', ''), unit=unit, min_ngram=min_ngram,
                                                   max_ngram=max_ngram)
        result['tokens_1'] = content_1
        result['tokens_2'] = content_2
        result['tokens_3'] = content_3
        selected_dm = request.values.get('distance_metrics', '')
        strip_chars = ' "\''
        selected_dm = [d.strip(strip_chars).lower() for d in selected_dm.split(',') if d.strip(strip_chars)]
        if not selected_dm:
            selected_dm = distance_metrics

        result.update({
            'distances12': cal_distances(content_1, content_2, selected_dm),
            'distances23': cal_distances(content_2, content_3, selected_dm),
            'distances13': cal_distances(content_1, content_3, selected_dm)
        })

        return jsonify(result)


def cal_distances(content_1, content_2, selected_dm):
    distances = []
    for dm_name in selected_dm:
        sim_checker = get_similarity_checker(dm_name)
        if sim_checker:
            distances.append({dm_name: sim_checker(content_1, content_2)})
        else:
            distances.append({dm_name: 'Distance metric %s do not existed, we support only %s' %
                                       (dm_name, ', '.join(distance_metrics))})

    return distances

if __name__ == '__main__':
    # app.run(debug=True, host='107.170.109.238', port=8888)
    app.run(debug=True)
    # http_server = HTTPServer(WSGIContainer(app))
    # http_server.listen(8888)
    # IOLoop.instance().start()
