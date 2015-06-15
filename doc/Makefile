DBNAME = debsources

all: db-schema/ async-tasks

db-schema/:
	mkdir -p $@
	cd $@ && postgresql_autodoc -d $(DBNAME)
	cd $@ && ln -s $(DBNAME).html index.html

async-tasks:
	dot -Tpng async_tasks.dot > async_tasks.png

clean:
	rm -rf db-schema/
	rm async_tasks.png
