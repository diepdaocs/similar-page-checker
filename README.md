# Web pages similarity checking

[TOC]

# Overview
Mainly, we have 4 modules: Page Crawler, Page Extractor, Similarity Checker and Web Service
- Page Crawler: Crawl html content of web page. Currently, we use python [`requests`](https://github.com/kennethreitz/requests) library.
- Page Extractor: Extract content from raw html (remove html tag, unnecessary content,...). Currently, we use python [`dragnet`](https://github.com/seomoz/dragnet)  library.
- Similarity Checker: Calculate similarity between web pages content. The content is firstly `tokenizer` into tokens, after that generate [`ngram`](https://en.wikipedia.org/wiki/N-gram) (or shingles) tokens set, and finally apply [`distance metrics`](http://dataaspirant.com/2015/04/11/five-most-popular-similarity-measures-implementation-in-python/) to calculate similarity. Currently, we support three distance metrics are `jaccard`, `cosine` and `fuzzy`.
- Web Service: Build RESTful api services. Currently, we use python [flask](http://flask.pocoo.org/) (a micro web framework) and [Swagger UI](http://swagger.io/) for presenting API documents.

# Technologies
- Python 2.7

# Development
Install python libraries for Ubuntu
```shell
sudo apt-get install -y git python-dev python-pip build-essential libxml2-dev libxslt1-dev zlib1g-dev
```
Set up python virtual environment
```shell
virtualenv -p python2.7 venv
source ./venv/bin/activate
for lib in $(cat requirements.txt); do pip install $lib; done
```
Config IDE (e.g Pycharm) using created python `venv`: Go to `Preference` -> `Project` -> `Project Interpreter`

# Deployment
There 2 options:
- Docker swarm cluster (recommended): support scaling application, load balancing
- Standalone docker container

Install docker: for more options, please refer to [official page](https://docs.docker.com/install/linux/docker-ce/ubuntu/)
```shell
curl -fsSL get.docker.com -o get-docker.sh && sudo sh get-docker.sh
```
## Using [docker swarm cluster](https://docs.docker.com/get-started/) (recommended)
- Init docker swarm cluster: this machine will be the `master node`
```shell
docker swarm init
```
- [Optional] add more node to swarm cluster
```shell
docker swarm join --token [TOKEN] [MASTER_HOST:PORT]
```
- Deploy app: [Web + Redis + Monitor/Visualizer](docker-compose.yml)
```shell
docker stack deploy -c docker-compose.yml sim-check
```

- Useful commands
```shell
docker service ls
docker service logs -f sim-check_web
docker stack ps sim-check
docker stack rm sim-check
docker node ls
```
## Using standalone docker container
- Start redis
```shell
docker rm redis
docker run -d --name redis -p 6379:6379 redis
```
- Start web app (UI + RestAPI)

Note: remember to update `REDIS_HOST`
```shell
docker rm sim-check
docker run -d \
           --name sim-check \
           -p 8888:8888 \
           -e REDIS_HOST=192.168.1.118 \
           -e REDIS_PORT=6379 \
           -v `pwd`:/code \
           diepdao12892/webpages-duplicated-checking:1.0 \
           gunicorn -k tornado -w 2 -b 0.0.0.0:8888 main:app --max-requests 10000
```

- Useful commands
```shell
docker ps
docker logs -f sim-check
docker stop sim-check
docker start sim-check
docker restart sim-check
docker rm sim-check
```