NOSE = nosetests
FLAKE = flake8

SRCDIR = debsources
BINDIR = bin
TESTDIR = $(SRCDIR)/tests
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

test-travis:
	$(NOSE) $(TESTFLAGS) $(TESTDIR) -a \!notravis

test-coverage:
	$(NOSE) $(TESTFLAGS) $(TESTDIR) --with-coverage --cover-package=debsources

check:
	$(FLAKE) $(SRCDIR)/ $(shell grep -H 'env python' $(BINDIR)/debsources-* | cut -f 1 -d :)

clean:
	$(MAKE) -C doc $@


.PHONY: all doc test test-all test-fast test-slow check clean
