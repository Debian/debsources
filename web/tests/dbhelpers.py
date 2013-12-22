
import models
import os
import sqlalchemy
import subprocess


def pg_restore(dbname, dumpfile):
    subprocess.check_call(['pg_restore', '--dbname', dbname, dumpfile])


class DbTestFixture(object):

    def db_setup(self, dbname, dbdump, echo=False):
        self.db = sqlalchemy.create_engine('postgresql:///' + dbname, echo=echo)
        models.Base.metadata.drop_all(self.db)	# just in case...
        pg_restore(dbname, dbdump)
        self.Session = sqlalchemy.orm.sessionmaker()
        self.session = self.Session(bind=self.db)
        # models.Base.metadata.create_all(self.db)

    def db_teardown(self):
        self.session.rollback()
        self.session.close()
        models.Base.metadata.drop_all(self.db)
