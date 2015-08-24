#!/usr/bin/env python3

from flask.ext.wtf import Form
from wtforms import (   BooleanField, 
                        HiddenField, 
                        RadioField, 
                        SelectField, 
                        StringField, 
                        SubmitField, 
                        TextAreaField, 
                        validators, 
                    )
from flask_wtf.file import FileField, FileRequired

class DatasetUploadForm(Form):

    '''DatasetUploadForm is a WTForm Form object for uploading data files
    '''

    dataset_name = StringField('Dataset name:', [validators.Required(), validators.length(max=60)])
    data_file = FileField('Data file:', [validators.Required()])
    dataset_desc = TextAreaField('Description:', [validators.optional(), validators.length(max=500)])
    submit = SubmitField('Upload Data')