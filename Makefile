NOSE = nosetests
TESTFLAGS = -v

all:
	@echo 'Nothing to do by default, maybe you want "make test"?'
	@false

test: tests-fast

disttest:
	$(NOSE) $(TESTFLAGS) python/

tests-fast:
	$(NOSE) $(TESTFLAGS) python/ -a \!slow
tests-slow:
	$(NOSE) $(TESTFLAGS) python/ -a slow
