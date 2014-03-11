NOSE = nosetests
TESTFLAGS = -v

all:
	@echo 'Nothing to do by default, maybe you want "make test"?'
	@false

doc:
	$(MAKE) -C doc/

test: tests-fast

disttest:
	$(NOSE) $(TESTFLAGS) python/

tests-fast:
	$(NOSE) $(TESTFLAGS) python/ -a \!slow
tests-slow:
	$(NOSE) $(TESTFLAGS) python/ -a slow

clean:
	$(MAKE) -C doc $@
