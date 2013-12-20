all:
	@echo 'Nothing to do by default, maybe you want "make test"?'
	@false

test:
	nosetests python/
