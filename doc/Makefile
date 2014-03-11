DBNAME = debsources

all: db-schema/

db-schema/:
	mkdir -p $@
	cd $@ && postgresql_autodoc -d $(DBNAME)
	cd $@ && ln -s $(DBNAME).html index.html

clean:
	rm -rf db-schema/
