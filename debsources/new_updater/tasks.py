from __future__ import absolute_import

from debsources.new_updater.celery import app


@app.task
def print_package(pkg):
    print(pkg)

