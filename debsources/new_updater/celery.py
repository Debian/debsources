from __future__ import absolute_import

from celery import Celery

app = Celery('new_updater',
             broker='amqp://',
             backend='amqp://',
             include=['debsources.new_updater.tasks'])

if __name__ == '__main__':
    app.start()
