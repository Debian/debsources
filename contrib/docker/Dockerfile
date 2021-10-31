FROM debian:bullseye

ENV DEBIAN_FRONTEND noninteractive

# PACKAGES
RUN apt-get update && \
    apt-get install -y \
    apache2 \
    libapache2-mod-wsgi-py3 \
    libjs-jquery \
    libjs-highlight.js \
    python3-debian \
    python3-flask \
    python3-magic \
    tango-icon-theme \
    debmirror \
    exuberant-ctags \
    python3-matplotlib \
    python3-psycopg2 \
    python3-sqlalchemy \
    sloccount \
    python3-nose \
    python3-nose2-cov \
    python3-flaskext.wtf \
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

# Apache
ADD debsources.conf /etc/apache2/sites-enabled/
RUN rm /etc/apache2/sites-enabled/000-default.conf

ENV PYTHONPATH /opt/debsources/lib/

EXPOSE 5000
