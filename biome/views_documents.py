#!/usr/bin/env python3

from flask import ( Blueprint, 
                    current_app, 
                    jsonify, 
                    redirect, 
                    render_template, 
                    request, 
                    url_for, 
                    )
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
from werkzeug import secure_filename
from flask_wtf.file import FileField, FileRequired
from biome import ( api, 
                    app, 
                    data, 
                    db, 
                    models, 
                    )
from tempfile import mkstemp
from hashlib import sha224
import re
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

    dataset_name = StringField('Dataset name:', [validators.Required(), validators.length(max=60)])
    data_file = FileField('Data file:', [validators.Required()])
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
        Saves files to UPLOAD_FOLDER if all are same type. 
        Returns file_ids (with new file IDs from database) if successful.
        Returns False or file_ids=[] if unsuccessful.
    '''

    dataset_name = upload_form.dataset_name.data
    filetype = upload_form.file_type.data.lower()
    if filetype == 'dta':
        file_extension = 'txt'
    else:
        file_extension = filetype
    description = upload_form.file_desc.data
    uploads_dir = app.config['UPLOAD_FOLDER']+'/'

    # check to make sure all files are of same type
    if not all([file_obj.filename.lower().endswith(file_extension) for file_obj in files]):
        return False

    try:
        dataset_id = save_new_dataset(dataset_name, description)
    except: # look up database-specific exceptions for here
        return False

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

    file_ids = []
    
    for file_obj in files:
        try:
            tmp_file_path = mkstemp()[1]
            file_obj.save(tmp_file_path)
            hash_val = get_hash(tmp_file_path)

            new_file_path = uploads_dir+hash_val+secure_filename(file_obj.filename)[-4:]
            shutil.move(tmp_file_path, new_file_path)

            app.logger.info('Saved uploaded file {} to {}'.format(file_obj.filename, new_file_path))

            file_ids.append(save_new_file_to_db(dataset_id, new_file_path))

        except:
            return False
    else: # for loop completed successfully
        return file_ids

def save_new_dataset(dataset_name, description):

    ''' Creates a new row in the Dataset db table
    '''

    new_dataset = models.Dataset(dataset_name, description)
    db.session.add(new_dataset)
    db.session.commit()

    app.logger.info('Saved new dataset {} to database'.format(dataset_name))

    return new_dataset.id

def save_new_ms2_file(dataset_id, file_path):

    ''' Creates a new row in the ms2_file db table
    '''

    new_ms2_file = models.MS2File(file_path, dataset_id)
    db.session.add(new_ms2_file)
    db.session.commit()

    app.logger.info('Saved new MS2 file {} (Dataset ID {}) to database'.format(file_path, dataset_id))

    return new_ms2_file.id

def save_new_dta_file(dataset_id, file_path):

    ''' Creates a new row in the dta_file db table
    '''

    # parse DTA file for 'flags' field... (something like '-p 2 -m 0 --trypstat')

    new_dta_file = models.DTAFile(file_path, dataset_id)
    db.session.add(new_dta_file)
    db.session.commit()

    app.logger.info('Saved new DTA file {} (Dataset ID {}) to database'.format(file_path, dataset_id))

    return new_dta_file.id

def save_new_sqt_file(dataset_id, file_path):

    ''' Creates a new row in the sqt_file db table
    '''

    new_sqt_file = models.SQTFile(file_path, dataset_id)
    db.session.add(new_sqt_file)
    db.session.commit()

    app.logger.info('Saved new SQT file {} (Dataset ID {}) to database'.format(file_path, dataset_id))

def save_new_ms1_file(dataset_id, file_path):

    ''' Creates a new row in the ms1_file db table
    '''

    raise NotImplementedError
    # new_ms1_file = models.MS1File(file_path, dataset_id)
    # db.session.add(new_ms1_file)
    # db.session.commit()

    # app.logger.info('Saved new MS1 file {} (Dataset ID {}) to database'.format(file_path, dataset_id))

    # return new_ms1_file.id

def check_file_types(filename_list):

    ''' Checks incoming files for correct file extensions
        and file names. Returns True if all OK, False if not.
    '''

    accepted_file_extensions = {'ms2',
                                'sqt',
                                'txt', # DTASelect-filter.txt
                                'ms1',
                                }

    # check to make sure all filenames end in a correct extension
    if not all([filename[-3:].lower() in accepted_file_extensions for filename in filename_list]):
        return False

    # check to make sure all '.txt' files also end with 'DTASelect-filter.txt'
    potential_dta_files = [filename for filename in filename_list if filename.endswith('.txt')]
    if not all([re.search(r'^.+DTASelect-filter.txt$', filename) for filename in potential_dta_files]):
        return False

    return True

@data.route('/', methods=('GET', 'POST'))
def document_index():
    upload_form = SubmitForm()

    if upload_form.validate_on_submit():

        files = request.files.getlist('data_file')
        filenames = [file_obj.filename for file_obj in files]
        app.logger.info('User trying to upload files {}'.format(', '.join(filenames)))

        if not check_file_types(filenames):
            return 'Can\'t upload all of those file types... {}'.format(', '.join(filenames)) # this should return a redirect to a different view/AJAX response

        # file_ids = validate_and_save(files, upload_form)

        # if not file_ids:
        #     app.logger.error('Saving uploaded dataset {} failed'.format(', '.join(filenames)))
        #     file_ids = None

        # return redirect(url_for('data.upload_view', filenames=filenames, file_ids=file_ids, file_type=upload_form.file_type.data.lower()))

        return redirect(url_for('data.upload_view'))

    return render_template('data/document_index.html', upload_form=upload_form)


@data.route('/uploadview')
def upload_view():
    ## convert this to an ajax response

    # filenames = request.args.get('filenames', None)
    # file_ids = request.args.get('file_ids', None)
    # file_type = request.args.get('file_type', None)

    # return 'Successfully uploaded files: {}'.format(filenames)
    return 'Successfully uploaded files'

