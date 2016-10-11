# Web pages similarity checking #

[TOC]

# Overview #
## Mainly, we have 4 modules: Page Crawler, Page Extractor, Similarity Checker and Web Service ##
* Page Crawler: Crawl html content of web page. Currently, we use python [`requests`](https://github.com/kennethreitz/requests) library.
* Page Extractor: Extract content from raw html (remove html tag, unnecessary content,...). Currently, we use python [`dragnet`](https://github.com/seomoz/dragnet)  library.
* Similarity Checker: Calculate similarity between web pages content. The content is firstly `tokenizer` into tokens, after that generate [`ngram`](https://en.wikipedia.org/wiki/N-gram) (or shingles) tokens set, and finally apply [`distance metrics`](http://dataaspirant.com/2015/04/11/five-most-popular-similarity-measures-implementation-in-python/) to calculate similarity. Currently, we support three distance metrics are `jaccard`, `cosine` and `fuzzy`.
* Web Service: Build RESTful api services. Currently, we use python [flask](http://flask.pocoo.org/) (a micro web framework) and [Swagger UI](http://swagger.io/) for presenting API documents.
# Setup #
## Install python environment libraries for Ubuntu ##
```
#!shell
sudo apt-get install -y git python-dev python-pip build-essential libxml2-dev libxslt1-dev zlib1g-dev python3-pip
sudo pip install virtualenvwrapper
source `which virtualenvwrapper.sh` && echo "source `which virtualenvwrapper.sh`" >> ~/.bashrc && echo "[[ -r ~/.bashrc ]] && . ~/.bashrc" >> ~/.bash_profile

```
## Install python project virtual environment ##
Create virtual environment
```
#!shell
mkvirtualenv webpages-duplicated-checking

```
Active virtual environment (Remember to active virtual environment before run service)
```
#!shell
workon webpages-duplicated-checking

```
## Get source code and install requirement library into virtual environment ##
### Clone source code ###
```
#!shell
git clone https://diepdt@bitbucket.org/diepdt/webpages-duplicated-checking.git

```
### Install library (All python requirement libraries has been put in `requirements.txt` file) ###
```
#!shell
cd webpages-duplicated-checking/
workon webpages-duplicated-checking
pip install -r requirements.txt

```
## Run webpages-duplicated-checking service ##
```
#!shell
cd webpages-duplicated-checking/
screen -R webpages-duplicated-checking
workon webpages-duplicated-checking
python main.py

```
## Monitor and view service logs ##
View service
```
#!shell
screen -r webpages-duplicated-checking

```
To stop service, press Ctrl + C.
To start service:
```
#!shell
workon webpages-duplicated-checking
python main.py

```
# API #
## All the api has been documented in [Swagger UI](http://swagger.io/) ##
* After run service by `python mani.py`, you can access to the Swagger UI by url `http://[HOST]:[PORT]/doc`, please view `main.py` file to see where the server host and port has been deployed. For example [http://107.170.109.238:8888/doc/](http://107.170.109.238:8888/doc/).
* You can change to `host` and `port` from `app.run(debug=True, host='107.170.109.238', port=8888)` line in `main.py`. You can run service in debug mode by set parameter `debug=True`.
* You can try the API calls and view API documents directly from Swagger UI.

# Fully deploy to production #
* For scaling, you must run application service under [gunicorn](http://flask.pocoo.org/docs/0.10/deploying/wsgi-standalone/) because flask is a single-thread application.
* Replace the `python main.py` above command by `gunicorn -w 2 -b 107.170.109.238:8888 main:app`. `-w [NUM OF WORKER PROCESS]` - Number of processor. `-b [HOST]:[PORT]` - Host and port to deploy service. `-D` - Run gunicorn as a deamon process.
* When run `gunicorn` as daemon, if you want to view log, use command:
```
#!shell
tail -f logs/[DATE].log
```
* If you want to run `Flask` and `gunicorn` under `nginx` server, use following tutorial: [How to Run Flask Applications with Nginx Using Gunicorn](http://www.onurguzel.com/how-to-run-flask-applications-with-nginx-using-gunicorn/). Below is `nginx` config server: `sudo vi /etc/nginx/sites-available/webpage-similarity`
```
#!shell
server {
    listen 80;
    server_name 107.170.109.238;
    access_log  /var/log/nginx/webpage-similarity.log;

    location / {
        proxy_pass http://127.0.0.1:8888;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```
```
sudo ln -s /etc/nginx/sites-available/webpage-similarity /etc/nginx/sites-enabled/webpage-similarity
sudo nginx -t
service nginx reload
```
* If you want run application under `supervisor`, please following this tutorial [How To Install and Manage Supervisor](https://www.digitalocean.com/community/tutorials/how-to-install-and-manage-supervisor-on-ubuntu-and-debian-vps) to set up `supervisor` and config the application as following: `sudo vi /etc/supervisor/conf.d/webpage-similarity.conf`
```
#!shell
[program:webpage-similarity]
command=/home/root/virtualenvs/webpages-duplicated-checking/bin/python /home/root/virtualenvs/webpages-duplicated-checking/bin/gunicorn -w 4 -b 107.170.109.238:8888 main:app
directory=/root/webpages-duplicated-checking
autostart=true
autorestart=true
stdout_logfile=/var/log/wepage-similarity.out.log
redirect_stderr=true
```
```
sudo supervisorctl reread
sudo supervisorctl update
```

# Upgrade to new version #
This is step by step:
1. Update source code: `git pull`  
2. Install new libraries: `pip install -r requirements.txt`  
If any errors, run this command to install required libs in ubuntu: `sudo apt-get update && sudo apt-get install -y libxml2-dev libxslt1-dev zlib1g-dev libjpeg62-turbo-dev`  
3. Restart program in supervisord: `sudo supervisorctl restart webpage-similarity`