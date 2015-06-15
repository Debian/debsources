from __future__ import absolute_import

from .celery import app

from debsources import fs_storage, db_storage
from debsources.sqla_session import _get_engine_session

from celery import Task

import os
import six
import subprocess


engine, session = _get_engine_session('postgresql:///debsources',
                                      verbose=False)


# Base class for tasks accessing the database
class DBTask(Task):
    """Abstract class for tasks accessing the database. Ensures that the
session is returned to the session pool at the end of the execution

    From
    http://prschmid.blogspot.fr/2013/04/using-sqlalchemy-with-celery-tasks.html

    """
    abstract = True

    def after_return(self, *args, **kwargs):
        session.remove()


# hooks

@app.task
def run_shell_hooks(pkg, event):
    pass


@app.task
def call_hooks(pkg, event):
    pass


# main tasks

# extract new packages

@app.task
def extract_new(mirror):
    for pkg in mirror.ls():
        s = add_package.s(pkg.description('testdata/sources'))
        s.delay()


@app.task(base=DBTask)
def add_package(pkg):
    pkgdir = pkg['extraction_dir']
    try:
        fs_storage.extract_package(pkg, pkgdir)
    except subprocess.CalledProcessError as e:
        print('extract error: {0} -- {1}'.format(e.returncode,
                                                 ' '.join(e.cmd)))
    else:
        with session.begin_nested():
            os.chdir(pkgdir)
            db_storage.add_package(session, pkg, pkgdir, False)
            s = call_hooks.s(pkg, 'add-package')
            s.delay()


# update suites

@app.task(base=DBTask)
def add_suite_package(suite, pkg_id):
    pass


@app.task
def update_suites(mirror):
    for (suite, pkgs) in six.iteritems(mirror.suites):
        for pkg_id in pkgs:
            s = add_suite_package.delay(suite, pkg_id)
            s.delay()
    pass


# update metadata

@app.task
def update_metadata(mirror):
    pass


# collect garbage

@app.task
def garbage_collect(mirror):
    for pkg in mirror.ls():
        s = rm_package.s(pkg.description())
        s.delay()


@app.task(base=DBTask)
def rm_package(pkg):
    print('deleting: {0}-{1}'.format(pkg['package'], pkg['version']))


# end callback

@app.task
def finish(res):
    print('Update finished.')
