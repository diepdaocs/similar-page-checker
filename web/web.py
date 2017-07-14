import os
import time
from datetime import datetime
from multiprocessing import Pool, cpu_count, Process
from uuid import uuid4

import pandas as pd
from flask import render_template, request, send_from_directory, jsonify, url_for
from redis import StrictRedis
from werkzeug.utils import secure_filename, redirect

from api import get_similarity_checker
from app import app
from similarity_checker import tokenize_and_normalize_content
from util.utils import get_logger

# This is the path to the upload directory
app.config['UPLOAD_FOLDER'] = 'web/upload'
# These are the extension that we are accepting to be uploaded
excel_extensions = {'xls', 'xlsx'}
sup_file_type = {'csv', 'txt'} | excel_extensions
app.config['ALLOWED_EXTENSIONS'] = sup_file_type
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # Accept max 1GB file


logger = get_logger(__name__)

redis = StrictRedis(db=1)


# For a given file, return whether it's an allowed type or not
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']


def is_excel_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in excel_extensions


@app.route('/ui')
def index():
    return render_template('index.html')


@app.route('/similarity/batch-cross-check', methods=['POST'])
def cross_check_sim():
    job_id = str(uuid4())
    # Get form parameters
    selected_dm = request.values.get('distance_metric') or 'cosine'
    unit = request.values.get('unit') or 'word'
    min_ngram = int(request.values.get('min_ngram')) or 1
    max_ngram = int(request.values.get('max_ngram')) or 1

    file_text = request.files.get('file_text')
    if not file_text or not allowed_file(file_text.filename):
        return render_template('message.html', message='ERROR: File type is not supported, supported file type is %s'
                                                       % ', '.join(sup_file_type))

    file_com = os.path.splitext(secure_filename(file_text.filename))
    file_text_name = file_com[0]
    file_text_path = os.path.join(app.config['UPLOAD_FOLDER'], '%s_input-with-job_%s%s' %
                                  (file_text_name, job_id, file_com[1]))
    file_text.save(file_text_path)
    try:
        if is_excel_file(file_text.filename):
            df = pd.read_excel(file_text_path, encoding='utf-8')
        else:
            df = pd.read_csv(file_text_path, delimiter='\t', encoding='utf-8')
    except UnicodeDecodeError, e:
        logger.exception(e)
        return render_template('message.html', message='ERROR: Your input file "%s" must be in UTF-8 encoding'
                                                       % file_text.filename)
    except Exception, e:
        logger.exception(e)
        return render_template('message.html', message='ERROR: Failed to read file "%s": %s'
                                                       % (file_text.filename, e.message))

    # Check required fields
    require_fields = ['content1', 'content2', 'content3']
    missing_fields = []
    for field in require_fields:
        if field not in df:
            missing_fields.append(field)
    if missing_fields:
        return render_template('message.html', message='ERROR: File "%s" must contain "%s" field(s)'
                                                       % (file_text.filename, ', '.join(missing_fields)))
    output_file = '%s_result-for-job_%s.csv' % (file_text_name, job_id)
    process = Process(target=process_job, args=(df, selected_dm, unit, min_ngram, max_ngram, job_id, output_file))
    process.start()

    return redirect(url_for('job_list'))


@app.route('/job-redirect')
def job_redirect():
    job_id = request.values.get('job_id')
    return redirect(url_for('job', job_id=job_id))


@app.route('/job')
def job_list():
    return render_template('job_list.html')


@app.route('/job/update')
def update_jobs():
    jobs = []
    for h in redis.keys():
        jb = redis.hgetall(h)
        jb['id'] = h
        jobs.append(jb)

    jobs = sorted(jobs, key=lambda j: j.get('start', 0), reverse=True)
    for jb in jobs:
        jb['start'] = datetime.fromtimestamp(float(jb['start'])).strftime('%Y-%m-%d %H:%M:%S')
        jb['complete'] = round(float(jb.get('progress', 0)) / float(jb['size']) * 100, 0) if float(jb['size']) else 0
        jb['finish'] = int(jb['finish']) == 1
    return jsonify(jobs=jobs)


@app.route('/job/<job_id>')
def job_info(job_id):
    output_file = 'result-for-job_%s.csv' % job_id
    return render_template('job.html', job_id=job_id, output_file=output_file)


def process_job(df, selected_dm, unit, min_ngram, max_ngram, job_id, output_file):
    # sim_checker = get_similarity_checker(selected_dm)
    df['distance12'] = ''
    df['distance23'] = ''
    df['distance13'] = ''
    redis.hset(job_id, 'size', len(df.index))
    redis.hset(job_id, 'start', time.time())
    redis.hset(job_id, 'file', output_file)
    redis.hset(job_id, 'finish', 0)
    tasks = [(row['content1'], row['content2'], row['content3'], selected_dm, unit, min_ngram, max_ngram, job_id)
             for idx, row in df.iterrows()]

    pool = Pool(cpu_count() * 2)
    result = pool.map(cross_check_similarity_wrapper, tasks)
    pool.close()
    pool.terminate()
    for idx, row in df.iterrows():
        df.loc[idx, 'distance12'] = result[idx]['distance12']
        df.loc[idx, 'distance23'] = result[idx]['distance23']
        df.loc[idx, 'distance13'] = result[idx]['distance13']

    try:
        df.to_csv(os.path.join(app.config['UPLOAD_FOLDER'], output_file), index=False, sep='\t', encoding='utf-8')
        redis.hset(job_id, 'finish', 1)
    except Exception as e:
        logger.exception(e)


def cross_check_similarity_wrapper(args):
    return cross_check_similarity(*args)


def cross_check_similarity(content_1, content_2, content_3, selected_dm, unit, min_ngram, max_ngram, job_id):
    sim_checker = get_similarity_checker(selected_dm)
    tokens_1 = tokenize_and_normalize_content(content_1, unit=unit,
                                              min_ngram=min_ngram,
                                              max_ngram=max_ngram)

    tokens_2 = tokenize_and_normalize_content(content_2, unit=unit, min_ngram=min_ngram,
                                              max_ngram=max_ngram)
    tokens_3 = tokenize_and_normalize_content(content_3, unit=unit, min_ngram=min_ngram,
                                              max_ngram=max_ngram)
    redis.hincrby(job_id, 'progress')

    return {
        'distance12': sim_checker(tokens_1, tokens_2),
        'distance23': sim_checker(tokens_2, tokens_3),
        'distance13': sim_checker(tokens_1, tokens_3),
    }


@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)


@app.route('/get-progress/<job_id>')
def get_progress(job_id=None):
    jb = redis.hgetall(job_id) or {}
    return jsonify(total=jb.get('size') or 0, finished=jb.get('progress') or 0)
