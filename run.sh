#!/bin/bash
export PYTHONPATH=/root/webpages-duplicated-checking
HOST=0.0.0.0
PORT=8888
fuser -k -n tcp $PORT
/home/root/virtualenvs/webpages-duplicated-checking/bin/python /home/root/virtualenvs/webpages-duplicated-checking/bin/gunicorn -k tornado -w 2 -b $HOST:$PORT main:app --max-requests 10000
