#!/bin/bash
export PYTHONPATH=/root/webpages-duplicated-checking
PORT=888
fuser -k -n tcp $PORT
/home/root/virtualenvs/webpages-duplicated-checking/bin/python /home/root/virtualenvs/webpages-duplicated-checking/bin/gunicorn -k tornado -w 2 -b 107.170.109.238:$PORT main:app --max-requests 10000
