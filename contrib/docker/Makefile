DOCKER_EXEC = docker exec
CONTAINER = docker_debsources_1
MAKE = make -C /opt/debsources/
TEST_TARGETS = test test-all test-fast test-slow test-ci test-coverage
SRC_TARGETS = all doc check clean test-online-app

.PHONY: build update-db run attach init-db $(SRC_TARGETS) $(TEST_TARGETS)

build:
	docker-compose build --pull

update-db:
	docker-compose run debsources /opt/db-update

run:
	docker-compose up -d

stop:
	docker-compose stop

start-apache:
	$(DOCKER_EXEC) -it $(CONTAINER) apache2ctl start

attach:
	$(DOCKER_EXEC) -it $(CONTAINER) /bin/bash

init-db:
	$(DOCKER_EXEC) $(CONTAINER) /opt/db-init

$(SRC_TARGETS):
	$(DOCKER_EXEC) $(CONTAINER) $(MAKE) $@

$(TEST_TARGETS): run init-db
	$(DOCKER_EXEC) $(CONTAINER) $(MAKE) $@
