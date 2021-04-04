.PHONY: build update-db run attach

build:
	docker-compose build --pull

update-db:
	docker-compose run debsources /opt/db-update

run:
	docker-compose up -d

start-apache:
	docker exec -it docker_debsources_1 apache2ctl start

attach:
	docker exec -it docker_debsources_1 /bin/bash

tests:
	docker exec docker_debsources_1 /opt/run-tests
