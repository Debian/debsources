Roles management
================

* The updater must have read-write rights on debsources tables and
  sequences. To enable it, run for example in a psql session:
# grant select,insert, update, delete on all tables in schema public to debsource_updater;
# grant select, update on all sequences in schema public to debsource_updater;

* The web application must have read rights on debsources tables:
# grant select on all tables in schema public to debsource_webapp;

You can specify in your config files different `db_uri` in different sections.

Performance tuning
==================

https://wiki.postgresql.org/wiki/Tuning_Your_PostgreSQL_Server

buffers
-------

# sysctl -w kernel.shmmax=17179869184
# sysctl -w kernel.shmall=4194304

then save into /etc/sysctl.conf

shared_buffers = 12 GB


cache
-----

effective_cache_size = 16GB


checkpoints
-----------

checkpoint_segments = 256	# i.e. every 4 GB


Trigram index
=============

http://www.postgresql.org/docs/9.1/static/pgtrgm.html

To enable trigram indexes (used for the file table) you'll need, on a per DB
basis:

  CREATE EXTENSION pg_trgm;

Then, for instance:

  CREATE INDEX ix_files_path_trgm
  ON files
  USING gin (encode(path, 'escape') gin_trgm_ops);

which can be queried efficiently using queries like:

  SELECT *
  FROM files
  WHERE encode(path, 'escape') LIKE '%stdio%';
