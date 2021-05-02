NOSE = nosetests3
FLAKE = flake8 --max-line-length 88 --ignore=E203,W503
# E203 (whitespace before ':') conflicts with black formatting
# W503 (line break before binary operator), ditto
BLACK = black
ISORT = isort --profile black --dont-follow-links -p debsources

SRCDIR = lib/debsources
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

test-coverage:
	$(NOSE) $(TESTFLAGS) $(TESTDIR) --with-coverage --cover-package=debsources

check:
	$(FLAKE) $(SRCDIR)/ $(shell grep -H 'env python' $(BINDIR)/debsources-* | cut -f 1 -d :)
	$(BLACK) --check $(SRCDIR)
# deactivated for now - until isort>=5 is available on Alpine Linux for CICD pipeline
# $(ISORT) --check $(SRCDIR) $(BINDIR)

format:
	$(BLACK) $(SRCDIR)
	$(ISORT) $(SRCDIR) $(BINDIR)

test-online-app:
	contrib/test-online-app

clean:
	$(MAKE) -C doc $@


.PHONY: all doc test test-all test-fast test-slow check clean
