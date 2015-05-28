FROM debian:jessie
# jessie is needed for libjs-highlight

MAINTAINER The Debsources developers <info@sources.debian.net>

ENV DEBIAN_FRONTEND noninteractive

# PACKAGES
RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y \
    apache2 \
    libapache2-mod-fcgid \
    libapache2-mod-wsgi \
    libjs-highlight \
    python-debian \
    python-flask \
    python-flup \
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
    python-setuptools \
    supervisor

### DEBSOURCES
RUN mkdir /etc/debsources
ENV PYTHONPATH /opt/debsources


# SCRIPTS

# Default command
ADD run.sh /run.sh
RUN chmod a+x /run.sh

# Allows to update the debsources postgres database
ADD update.sh /update.sh
RUN chmod a+x /update.sh

# Disable the default vhost in apache
RUN rm /etc/apache2/sites-enabled/000-default.conf

# Copy our config file for debsources (Note: the postgres' database address 
# is 'database'. This is done by linking the two containers together and
# naming them in a special manner (see the docker-compose.yml file)
ADD config.ini /etc/debsources/

ADD etc /etc

# Runs the supervisord (apache), as well as debsources itself
CMD ["/run.sh"]
