#!/bin/sh

/opt/debsources/bin/debsources-dbadmin --createdb postgresql://docker:docker@database:5432/debsources
/opt/debsources/bin/debsources-update
