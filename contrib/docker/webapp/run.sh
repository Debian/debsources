#!/bin/sh

/usr/bin/supervisord

/opt/debsources/bin/debsources-run-app --host=0.0.0.0
