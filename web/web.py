import os
import time
from datetime import datetime
from multiprocessing import Pool, cpu_count
from threading import Thread
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

redis = StrictRedis(
    db=1, host=os.environ.get('REDIS_HOST', 'localhost'), port=os.environ.get('REDIS_PORT', 6379))


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
    min_ngram = int(request.values.get('min_ngram') or 1)
    max_ngram = int(request.values.get('max_ngram') or 1)

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

    df = df.fillna('')
    # Check required fields
    min_no_field = 2
    if len(df.columns) < min_no_field:
        return render_template('message.html', message='ERROR: File "%s" must contain at least %d fields'
                                                       % (file_text.filename, min_no_field))
    output_file = '%s_result-for-job_%s.csv' % (file_text_name, job_id)
    thread = Thread(target=process_job, args=(df, selected_dm, unit, min_ngram, max_ngram, job_id, output_file))
    thread.setDaemon(True)
    thread.start()

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


def gen_distance_cols(columns):
    distance_cols = []
    no_col = len(columns)
    for i in range(no_col):
        for j in range(i + 1, no_col):
            distance_cols.append('Distance-%s-%s' % (columns[i], columns[j]))

    return distance_cols


def process_job(df, selected_dm, unit, min_ngram, max_ngram, job_id, output_file):
    columns = df.columns
    distance_cols = gen_distance_cols(columns)

    for col in distance_cols:
        df[col] = ''

    redis.hset(job_id, 'size', len(df.index))
    redis.hset(job_id, 'start', time.time())
    redis.hset(job_id, 'file', output_file)
    redis.hset(job_id, 'finish', 0)

    tasks = [(tuple(row[col] for col in columns), selected_dm, unit, min_ngram, max_ngram, job_id)
             for idx, row in df.iterrows()]

    pool = Pool(cpu_count())
    result = pool.map(cross_check_similarity_wrapper, tasks)
    pool.close()
    pool.terminate()
    for idx, row in df.iterrows():
        for dist_idx, col in enumerate(distance_cols):
            df.loc[idx, col] = result[idx][dist_idx]

    try:
        df.to_csv(os.path.join(app.config['UPLOAD_FOLDER'], output_file), index=False, sep='\t', encoding='utf-8')
        redis.hset(job_id, 'finish', 1)
    except Exception as e:
        logger.exception(e)


def cross_check_similarity_wrapper(args):
    return cross_check_similarity(*args)


def cross_check_similarity(contents, selected_dm, unit, min_ngram, max_ngram, job_id):
    sim_checker = get_similarity_checker(selected_dm)

    content_tokens = []
    for content in contents:
        content_tokens.append(tokenize_and_normalize_content(
            content, unit=unit, min_ngram=min_ngram, max_ngram=max_ngram))

    redis.hincrby(job_id, 'progress')

    no_col = len(contents)
    distances = []
    for i in range(no_col):
        for j in range(i + 1, no_col):
            distances.append(sim_checker(content_tokens[i], content_tokens[j]))

    return distances


@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)


@app.route('/get-progress/<job_id>')
def get_progress(job_id=None):
    jb = redis.hgetall(job_id) or {}
    return jsonify(total=jb.get('size') or 0, finished=jb.get('progress') or 0)
