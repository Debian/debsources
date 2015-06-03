from __future__ import absolute_import

from .celery import app

import six


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
        s = add_package.s(pkg.description())
        s.delay()


@app.task
def add_package(pkg):
    print('adding: {0}-{1}'.format(pkg['package'], pkg['version']))


# update suites

@app.task
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


@app.task
def rm_package(pkg):
    print('deleting: {0}-{1}'.format(pkg['package'], pkg['version']))


# end callback

@app.task
def finish(res):
    print('Update finished.')
