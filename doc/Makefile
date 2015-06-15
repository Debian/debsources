DBNAME = debsources

all: db-schema/ async_tasks.png

db-schema/:
	mkdir -p $@
	cd $@ && postgresql_autodoc -d $(DBNAME)
	cd $@ && ln -s $(DBNAME).html index.html

async_tasks.png: async_tasks.dot
	dot -Tpng async_tasks.dot > async_tasks.png

clean:
	rm -rf db-schema/
	rm -f async_tasks.png
