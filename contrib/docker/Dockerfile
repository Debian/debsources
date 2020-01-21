FROM debian:buster
MAINTAINER Matthieu Caneill <matthieu.caneill@gmail.com>

ENV DEBIAN_FRONTEND noninteractive

# PACKAGES
RUN apt-get update && \
    apt-get install -y \
    libjs-jquery \
    libjs-highlight \
    python-debian \
    python-flask \
    python-magic \
    tango-icon-theme \
    debmirror \
    exuberant-ctags \
    python-matplotlib \
    python-psycopg2 \
    python-sqlalchemy \
    sloccount \
    python-nose \
    python-nose2-cov \
    python-flaskext.wtf \
    dpkg-dev \
    diffstat \
    netcat \
    git \
    postgresql-client

# SETUP
ADD scripts/* /opt/
RUN mkdir /etc/debsources
ADD config.ini /etc/debsources/
RUN mkdir /opt/debsources

ENV PYTHONPATH /opt/debsources/lib/

EXPOSE 5000
