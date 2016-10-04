FROM amitkgupta/python-2.7-machine-learning

MAINTAINER Diep Dao <diepdao12892@gmail.com>

RUN apt-get update \
    && apt-get install -y libxml2-dev libxslt1-dev zlib1g-dev libjpeg62-turbo-dev

ENV PYTHONUNBUFFERED 1
RUN mkdir /code
WORKDIR /code
ADD requirements.txt /code/
RUN pip install -U pip lxml Cython && pip install -r requirements.txt
