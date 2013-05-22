from app import db
import models

class Package_app(models.Package, db.Model):
    pass

class Version_app(models.Version, db.Model):
    pass

