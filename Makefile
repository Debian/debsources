NOSE = nosetests
TESTFLAGS = -v

all:
	@echo 'Nothing to do by default, maybe you want "make test"?'
	@false

doc:
	$(MAKE) -C doc/

test: tests-fast

disttest:
	$(NOSE) $(TESTFLAGS) debsources/

tests-fast:
	$(NOSE) $(TESTFLAGS) debsources/ -a \!slow
tests-slow:
	$(NOSE) $(TESTFLAGS) debsources/ -a slow

clean:
	$(MAKE) -C doc $@
