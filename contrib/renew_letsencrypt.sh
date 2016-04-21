#!/bin/sh

cd /etc/apache2/certs/letsencrypt/
acme-tiny --account-key account.key --csr domain.csr --acme-dir /srv/www/debsources/public_html/.well-known/acme-challenge > /tmp/signed.crt || exit
wget -O - https://letsencrypt.org/certs/lets-encrypt-x3-cross-signed.pem > intermediate.pem
cat /tmp/signed.crt intermediate.pem > chained.pem
rm /tmp/signed.crt
sudo service apache2 reload
