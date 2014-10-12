NOSE = nosetests
TESTFLAGS = -v

all:
	@echo 'Nothing to do by default, maybe you want "make test"?'
	@false

doc:
	$(MAKE) -C doc/

test: test-fast

test-all:
	$(NOSE) $(TESTFLAGS) debsources/

test-fast:
	$(NOSE) $(TESTFLAGS) debsources/ -a \!slow

test-slow:
	$(NOSE) $(TESTFLAGS) debsources/ -a slow

clean:
	$(MAKE) -C doc $@
