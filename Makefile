NOSE = nosetests
TESTDIR = debsources/tests/
TESTFLAGS = -v

all:
	@echo 'Nothing to do by default, maybe you want "make test"?'
	@false

doc:
	$(MAKE) -C doc/

test: test-fast

test-all:
	$(NOSE) $(TESTFLAGS) $(TESTDIR)

test-fast:
	$(NOSE) $(TESTFLAGS) $(TESTDIR) -a \!slow

test-slow:
	$(NOSE) $(TESTFLAGS) $(TESTDIR) -a slow

clean:
	$(MAKE) -C doc $@
