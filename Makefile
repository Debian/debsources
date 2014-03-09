NOSE = nosetests
TESTFLAGS = -v
DBNAME = debsources

all:
	@echo 'Nothing to do by default, maybe you want "make test"?'
	@false

doc: doc/db-schema/

doc/db-schema/:
	mkdir -p $@
	cd $@ && postgresql_autodoc -d $(DBNAME)

test: tests-fast

disttest:
	$(NOSE) $(TESTFLAGS) python/

tests-fast:
	$(NOSE) $(TESTFLAGS) python/ -a \!slow
tests-slow:
	$(NOSE) $(TESTFLAGS) python/ -a slow

clean:
	rm -rf doc/db-schema/
