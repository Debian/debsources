MAKE = make -C /opt/debsources/
TEST_TARGETS = test test-all test-fast test-slow test-coverage
SRC_TARGETS = all doc check clean test-online-app

.PHONY: build update-db run attach init-db $(SRC_TARGETS) $(TEST_TARGETS)

build:
	docker compose build --pull

update-db:
	docker compose run app /opt/db-update

run:
	docker compose up -d

logs:
	docker compose logs app

stop:
	docker compose stop

start-apache:
	docker compose exec app apache2ctl start

attach:
	docker compose exec app /bin/bash

init-db:
	docker compose exec app /opt/db-init

$(SRC_TARGETS):
	docker compose exec app $(MAKE) $@

$(TEST_TARGETS): run init-db
	docker compose exec app $(MAKE) $@
