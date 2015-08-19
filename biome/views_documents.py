#!/usr/bin/env python3

from flask import ( render_template, jsonify, 
                    Blueprint, current_app,
                    request, redirect, 
                    url_for, 
                    )
from flask.ext.wtf import Form
from wtforms import (   StringField, SubmitField, 
                        BooleanField, SelectField, 
                        RadioField, HiddenField, 
                        TextAreaField, validators, 
                    )
from werkzeug import secure_filename
from flask_wtf.file import FileField, FileRequired
from biome import ( app, api, 
                    data,
                    )
from tempfile import mkstemp
from hashlib import sha224
import shutil

file_types = [  ('MS2', 'MS2'),
                ('DTA', 'DTA'),
                ('SQT', 'SQT'),
                ('MS1', 'MS1')
            ]
file_extensions = ('ms2', 'sqt', 'txt', 'ms1')

class SubmitForm(Form):

    '''SubmitForm is a WTForm Form object for uploading data files
    '''

    file_name = StringField('Dataset name:', [validators.Required(), validators.length(max=60)])
    data_file = FileField('Data file:', [validators.Required()])
    file_type = RadioField('File type:', [validators.Required()], choices=file_types)
    file_desc = TextAreaField('Description:', [validators.optional(), validators.length(max=500)])
    submit = SubmitField('Upload Data')

def get_hash(filepath):

    ''' read filepath and return calculated SHA224 hex digest
    '''

    hasher = sha224()
    with open(filepath, 'rb') as f:
        while True:
            byte = f.read(1)
            if not byte:
                break
            hasher.update(byte)

    return hasher.hexdigest()

def validate_and_save(files, filetype):

    ''' checks to make sure each filename in "files" ends with "filetype";
        Saves files to UPLOAD_FOLDER if all are same type. Returns True for success.
    '''

    uploads_dir = app.config['UPLOAD_FOLDER']+'/'

    if all([file_obj.filename.lower().endswith(filetype.lower()) for file_obj in files]):
        for file_obj in files:
            try:
                tmp_file_path = mkstemp()[1]
                file_obj.save(tmp_file_path)
                hash_val = get_hash(tmp_file_path)

                new_file_path = uploads_dir+hash_val+secure_filename(file_obj.filename)[-4:]
                shutil.move(tmp_file_path, new_file_path)

                app.logger.info('Saved uploaded file {} to {}'.format(file_obj.filename, new_file_path))

            except:
                return False
        else:
            return True # for loop completed successfully

@data.route('/', methods=('GET', 'POST'))
def document_index():
    upload_form = SubmitForm()

    if upload_form.validate_on_submit():

        files = request.files.getlist('data_file')
        filenames = [file_obj.filename for file_obj in files]
        print(filenames)

        if not validate_and_save(files, upload_form.file_type.data):
            app.logger.error('Saving uploaded dataset {} failed'.format(', '.join(filenames)))
            filenames = None

        return redirect(url_for('data.upload_view', filenames=filenames))

    return render_template('data/document_index.html', upload_form=upload_form)


@data.route('/uploadview')
def upload_view():
    ## convert this to an ajax response

    if request.args.get('filenames', None):
        # filenames = ', '.join(request.args['filenames'])
        filenames = request.args['filenames']

    return 'Successfully uploaded files: {}'.format(filenames)

