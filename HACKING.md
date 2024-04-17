# Getting started with Debsources development

You have 2 documented ways to get a local Debsources environment:
either a local deployment directly in your OS, or within a Docker
container.

To test the updater, and subsequently run the webapp on it, you will need a
(partial) Debian source mirror on your development machine. To that end, you
might want to use the data from the Debsources testsuite, which is shipped via a
separate Git submodule rooted at testdata/, so:

$ cd debsources/
$ git submodule update --init

The testdata Git repository is ~150 MB, so it might take a while to retrieve.

## Local Debsources deployment

- clone the Debsources Git repository:

  $ git clone https://salsa.debian.org/qa/debsources.git
  or
  $ git clone git@salsa.debian.org:qa/debsources.git

- ensure the Python interpreter can find Debsources' Python modules:

  $ export PYTHONPATH=`pwd`/debsources/lib:"$PYTHONPATH"
  $ python -c 'import debsources' # if this fails, double-check $PYTHONPATH

- create a PostgreSQL database for use by Debsources, e.g.:

  $ createdb debsources

  (as user postgres or equivalent)

- create the DB schema:

  $ bin/debsources-dbadmin --createdb postgresql:///debsources

  where debsources is the DB name. The last parameter must be a valid
  SQLAlchemy database URL; see
  https://sqlalchemy.readthedocs.org/en/latest/core/engines.html#database-urls for
  details on how to connect to remote databases.

- $ cp etc/config.ini etc/config.local.ini

  (when etc/config.local.ini, debsources will ignore etc/config.ini, and use
  the ".local." variant as its main configuration file)

- edit etc/config.local.ini and adapt it to your needs.

  To play with Debsources for development reasons, it should be enough to
  change `db_uri` (the same you used above for bin/debsources-dbadmin) and
  `root_dir` (the absolute path of your local Debsources Git repo) in the
  top-level `[DEFAULT]` section of the configuration file.

  If you plan to use Flask's development server, setting the option
  serve_static_files to true will permit it to serve javascript files
  and icon images (normally statically served by Apache).

- do an update run:

  $ bin/debsources-update -vv

- run the webapp:

  $ bin/debsources-run-app

  - Running on http://127.0.0.1:5000/
  - Restarting with reloader

  you can now visit the above URL with your browser and verify that everything
  is OK.

## Docker container

- Ensure docker is installed and the service is running, then build
  the Debsources image (may take a while):

  $ cd contrib/docker
  $ make build

- Update DB data (may take a while):

  $ make update-db

- Run debsources web app:

  $ make run

  Debsources should be up and running in http://localhost:5000

- (optional) Attach terminal to the web container:

  $ make attach

You're ready for Debsources hacking! How about giving Debsources easy hacks a
go now? <http://deb.li/debsrceasy>

## Running tests

See [testing.md](doc/testing.md].

# Coding conventions

All new Debsources code should be [PEP8][1] compliant and pass [pyflakes][2]
validation. Before submitting patches, please make sure that the lines of code
they touch conform to such requirements.

Additionally, `black` [3] and `isort` [4] are used to format Python source
files.

[1]: https://www.python.org/dev/peps/pep-0008/
[2]: https://pypi.python.org/pypi/pyflakes
[3]: https://black.readthedocs.io/en/stable/
[4]: https://pycqa.github.io/isort/

If you develop on Debian(-based distros), a good way to apply formatting and
check that everything is good is:

    # apt-get install flake8 isort
    $ python3 -m pip install --user black
    $ make format
    $ make check

You can add a pre-commit hook to automatically test PEP8 compliance (might be
outdated):

    $ ln -s ../../contrib/git-pre-commit .git/hooks/pre-commit
