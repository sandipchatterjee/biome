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
                    data, db
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

def validate_and_save(files, upload_form):

    ''' checks to make sure each filename in "files" ends with "filetype";
        Saves files to UPLOAD_FOLDER if all are same type. Returns True for success.
    '''

    dataset_name = upload_form.file_name.data
    filetype = upload_form.file_type.data.lower()
    if filetype == 'dta':
        file_extension = 'txt'
    else:
        file_extension = filetype
    description = upload_form.file_desc.data
    uploads_dir = app.config['UPLOAD_FOLDER']+'/'

    # check to make sure all files are of same type
    if all([file_obj.filename.lower().endswith(file_extension) for file_obj in files]):

        save_new_dataset(dataset_name, description)
        if filetype == 'ms2':
            save_new_file_to_db = save_new_ms2_file
        elif filetype == 'dta':
            save_new_file_to_db = save_new_dta_file
        elif filetype == 'sqt':
            save_new_file_to_db = save_new_sqt_file
        elif filetype == 'ms1':
            save_new_file_to_db = save_new_ms1_file
        else: # unsupported filetype
            return False
        
        for file_obj in files:
            try:
                tmp_file_path = mkstemp()[1]
                file_obj.save(tmp_file_path)
                hash_val = get_hash(tmp_file_path)

                new_file_path = uploads_dir+hash_val+secure_filename(file_obj.filename)[-4:]
                shutil.move(tmp_file_path, new_file_path)

                app.logger.info('Saved uploaded file {} to {}'.format(file_obj.filename, new_file_path))

                save_new_file_to_db(dataset_id, new_file_path)

            except:
                return False
        else:
            return True # for loop completed successfully

def save_new_dataset(dataset_name, description):

    ''' Creates a new row in the Dataset db table
    '''

    app.logger.info('Saved new dataset {} to database'.format(dataset_name))

    raise NotImplementedError('Saving datasets not yet implemented')

    return True # should return dataset ID from db table

def save_new_ms2_file(dataset_id, file_path):

    ''' Creates a new row in the ms2_file db table
    '''

    raise NotImplementedError('MS2 file uploads not yet implemented')

    app.logger.info('Saved new MS2 file {} to database'.format(file_path))

    return True # should return new MS2_file_id

def save_new_dta_file(dataset_id, file_path):

    ''' Creates a new row in the dta_file db table
    '''

    # parse DTA file for 'flags' field... (something like '-p 2 -m 0 --trypstat')

    raise NotImplementedError

    app.logger.info('Saved new DTA file {} to database'.format(file_path))

    return True # should return new dta_file_id

def save_new_sqt_file(dataset_id, file_path):

    ''' Creates a new row in the sqt_file db table
    '''

    raise NotImplementedError

    app.logger.info('Saved new SQT file {} to database'.format(file_path))

    return True # should return new SQT_file_id

def save_new_ms1_file(dataset_id, file_path):

    ''' Creates a new row in the ms1_file db table
    '''

    raise NotImplementedError

    app.logger.info('Saved new MS1 file {} to database'.format(file_path))

    return True # should return new MS1_file_id

@data.route('/', methods=('GET', 'POST'))
def document_index():
    upload_form = SubmitForm()

    if upload_form.validate_on_submit():

        files = request.files.getlist('data_file')
        filenames = [file_obj.filename for file_obj in files]
        print(filenames)

        if not validate_and_save(files, upload_form):
            app.logger.error('Saving uploaded dataset {} failed'.format(', '.join(filenames)))
            filenames = None

        return redirect(url_for('data.upload_view', filenames=filenames))

    return render_template('data/document_index.html', upload_form=upload_form)


@data.route('/uploadview')
def upload_view():
    ## convert this to an ajax response

    filenames = request.args.get('filenames', None)

    return 'Successfully uploaded files: {}'.format(filenames)

