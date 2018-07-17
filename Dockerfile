FROM python:2.7-slim

MAINTAINER Diep Dao <diepdao12892@gmail.com>

RUN apt-get update \
    && apt-get install -y python-dev python-pip build-essential libxml2-dev libxslt1-dev zlib1g-dev

ENV PYTHONUNBUFFERED 1

RUN mkdir /code

WORKDIR /code

ADD requirements.txt /code/

RUN for lib in $(cat requirements.txt); do pip install $lib; done
