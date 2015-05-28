FROM debian:jessie

MAINTAINER The Debsources developers <info@sources.debian.net>

ENV DEBIAN_FRONTEND noninteractive

# PACKAGES
RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y postgresql-9.4


### POSTGRES

# Allow remote connections to postgres (necessary since the webapp lives in another container)
RUN sed -i "/^#listen_addresses/i listen_addresses='*'" /etc/postgresql/9.4/main/postgresql.conf && \
    sed -i "/^# DO NOT DISABLE\!/i # Allow access from any IP address" /etc/postgresql/9.4/main/pg_hba.conf && \
    sed -i "/^# DO NOT DISABLE\!/i host all all 0.0.0.0/0 md5\n\n\n" /etc/postgresql/9.4/main/pg_hba.conf

# needs to run postgres to create a user
USER postgres
RUN /etc/init.d/postgresql start && \
    psql --command "CREATE USER docker WITH SUPERUSER PASSWORD 'docker';" && \
    psql --command "CREATE USER root WITH SUPERUSER;" && \
    createdb -O docker debsources

EXPOSE 5432

CMD ["/usr/lib/postgresql/9.4/bin/postgres", "-D", "/var/lib/postgresql/9.4/main", "-c", "config_file=/etc/postgresql/9.4/main/postgresql.conf"]
