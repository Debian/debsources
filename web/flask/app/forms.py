from flask.ext.wtf import Form, TextField, Required

class SearchForm(Form):
    packagename = TextField('package name', validators=[Required()])
