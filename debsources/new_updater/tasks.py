from __future__ import absolute_import

from debsources.new_updater.celery import app


@app.task
def add_package(pkg):
    print('prout')
    print(pkg['package'])


@app.task
def extract_new(mirror):
    for pkg in mirror.ls():
        print('adding: {0}'.format(pkg['package']))
        s = add_package.s(pkg)
        s.delay()
