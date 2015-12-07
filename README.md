# Web pages similarity checking #

# Overview #
## Mainly, we have 3 module: Page Crawler, Page Extractor and Similarity Checker ##
* Page Crawler: Crawl html content of web page. Currently, we use python [`requests`](https://github.com/kennethreitz/requests) library.
* Page Extractor: Extract content from raw html (remove html tag, unnecessary content,...). Currently, we use python [`dragnet`](https://github.com/seomoz/dragnet)  library.
* Similarity Checker: Calculate similarity between web pages content. The content is firstly `tokenizer` into tokens, after that generate [`ngram`](https://en.wikipedia.org/wiki/N-gram) (or shingles) tokens set, and finally apply [`distance metrics`](http://dataaspirant.com/2015/04/11/five-most-popular-similarity-measures-implementation-in-python/) to calculate similarity. Currently, we support three distance metrics are `jaccard`, `cosine` and `fuzzy`.
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
## Get source code and install requirements into virtual environment ##

```
#!shell
git clone https://diepdt@bitbucket.org/diepdt/webpages-duplicated-checking.git
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
## All the api has been documents by [Swagger](http://swagger.io/) ##
* After run service by `python mani.py`, you can access to the Swagger UI by url `[HOST]:[PORT]/doc`, please view `main.py` file to see where the server host and port has been deployed. For example [http://107.170.109.238:8888/doc/](http://107.170.109.238:8888/doc/).
* You can change to `host` and `port` from `app.run(debug=True, host='107.170.109.238', port=8888)' line in `main.py`. You can run service in debug mode by set parameter `debug=True`.