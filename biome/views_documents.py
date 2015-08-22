#!/usr/bin/env python3

from flask import ( Blueprint, 
                    current_app,
                    flash,  
                    jsonify, 
                    redirect, 
                    render_template, 
                    request, 
                    session, 
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
    dataset_desc = TextAreaField('Description:', [validators.optional(), validators.length(max=500)])
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

def save_new_file(file_obj):

    ''' Saves a new file (specified by file_obj) to new_file_path by calculating
        its SHA224 hash and saving as 'SHA224_digest.[file_extension]'

        Returns new_file_path for new saved file.
    '''

    uploads_dir = app.config['UPLOAD_FOLDER']+'/'
    tmp_file_path = mkstemp()[1]
    file_obj.save(tmp_file_path)
    hash_val = get_hash(tmp_file_path)

    new_file_path = uploads_dir+hash_val+secure_filename(file_obj.filename)[-4:]
    shutil.move(tmp_file_path, new_file_path)

    app.logger.info('Saved uploaded file {} to {}'.format(file_obj.filename, new_file_path))

    return new_file_path

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

def save_new_dbsearch(dataset_id, params=None):

    ''' Creates a new DBSearch row
    '''

    new_dbsearch = models.DBSearch(dataset_id, params)
    db.session.add(new_dbsearch)
    db.session.commit()

    app.logger.info('Saved new DBSearch {} for Dataset ID {} to database'.format(new_dbsearch.id, dataset_id))

    return new_dbsearch.id

def save_new_ms1_record(dataset_id, file_path):

    ''' Creates a new row in the ms1_file db table
    '''

    new_ms1_file = models.MS1File(file_path, dataset_id)
    db.session.add(new_ms1_file)
    db.session.commit()

    app.logger.info('Saved new MS1 file {} (Dataset ID {}) to database'.format(file_path, dataset_id))

    return new_ms1_file.id

def save_new_ms2_record(dataset_id, file_path):

    ''' Creates a new row in the ms2_file db table
    '''

    new_ms2_file = models.MS2File(file_path, dataset_id)
    db.session.add(new_ms2_file)
    db.session.commit()

    app.logger.info('Saved new MS2 file {} (Dataset ID {}) to database'.format(file_path, dataset_id))

    return new_ms2_file.id

def save_new_dta_record(dataset_id, file_path):

    ''' Creates a new row in the dta_file db table
    '''

    # parse DTA file for 'flags' field... (something like '-p 2 -m 0 --trypstat')

    new_dta_file = models.DTAFile(file_path, dataset_id)
    db.session.add(new_dta_file)
    db.session.commit()

    app.logger.info('Saved new DTA file {} (Dataset ID {}) to database'.format(file_path, dataset_id))

    return new_dta_file.id

def save_new_sqt_record(dataset_id, file_path):

    ''' Creates a new row in the sqt_file db table
    '''

    new_sqt_file = models.SQTFile(file_path, dataset_id)
    db.session.add(new_sqt_file)
    db.session.commit()

    app.logger.info('Saved new SQT file {} (Dataset ID {}) to database'.format(file_path, dataset_id))

    return new_sqt_file.id

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
    if not all([re.search(r'^.*DTASelect-filter.txt$', filename) for filename in potential_dta_files]):
        return False

    return True

def get_recent_records(model_obj, creation_time_field, limit=5):
    ''' Returns the most recent [limit] records '''
    return model_obj.query.order_by(creation_time_field.desc()).limit(limit).all()

@data.route('/', methods=('GET', 'POST'))
def document_index():
    upload_form = SubmitForm()

    recent_five_datasets = get_recent_records(models.Dataset, models.Dataset.uploaded_time)
    # dataset_pks = [dataset.id for dataset in recent_five_datasets]
    # associated_ms2s = [models.MS2File.query.filter_by(dataset_id=dataset_id).all() for dataset_id in dataset_pks]
    # associated_ms2s_scans = [ms2_files.scans]
    # scans_for_ms2s = [sum(ms2_files)]

    if upload_form.validate_on_submit():

        files = request.files.getlist('data_file')
        filenames = [file_obj.filename for file_obj in files]
        app.logger.info('User trying to upload files {}'.format(', '.join(filenames)))

        if not check_file_types(filenames):
            return 'Can\'t upload all of those file types... {}'.format(', '.join(filenames)) # this should return a redirect to a different view/AJAX response

        # save new uploaded file data
        try:
            ms1_file_paths = [save_new_file(file_obj) for file_obj in files if file_obj.filename.endswith('.ms1')]
            ms2_file_paths = [save_new_file(file_obj) for file_obj in files if file_obj.filename.endswith('.ms2')]
            sqt_file_paths = [save_new_file(file_obj) for file_obj in files if file_obj.filename.endswith('.sqt')]
            dta_file_paths = [save_new_file(file_obj) for file_obj in files if file_obj.filename.endswith('.txt')]
        except:
            app.logger.error('Error saving new files')
            return 'Error saving new files'

        dataset_id = None
        dbsearch_id = None
        ms1_data_ids = []
        ms2_data_ids = []
        sqt_data_ids = []
        dta_data_ids = []

        # save new dataset in database
        dataset_name = upload_form.dataset_name.data
        dataset_description = upload_form.dataset_desc.data
        try:
            dataset_id = save_new_dataset(dataset_name, dataset_description)
        except:
            app.logger.error('Error creating new dataset {}'.format(dataset_name))
            return 'Error creating new dataset {}'.format(dataset_name) # should return a redirect/view

        if ms1_file_paths or ms2_file_paths:
            try:
                # save MS1 and MS2 records to database
                ms1_data_ids = [save_new_ms1_record(dataset_id, ms1_file_path) for ms1_file_path in ms1_file_paths]
                ms2_data_ids = [save_new_ms2_record(dataset_id, ms2_file_path) for ms2_file_path in ms2_file_paths]
            except:
                # log database error and return
                app.logger.error('Error saving new MS1/MS2 file info to database')
                return 'Error saving new MS1/MS2 file info to database'

        if sqt_file_paths or dta_file_paths:
            try:
                dbsearch_id = save_new_dbsearch(dataset_id) # create DBSearch
            except:
                # log DB error and return
                app.logger.error('Error saving new MS1/MS2 file info to database')
                return 'Error saving new MS1/MS2 file info to database'

            try:
                # save SQT and DTA records to database
                sqt_data_ids = [save_new_sqt_record(dbsearch_id, sqt_file_path) for sqt_file_path in sqt_file_paths]
                dta_data_ids = [save_new_dta_record(dbsearch_id, dta_file_path) for dta_file_path in dta_file_paths]
            except:
                app.logger.error('Error saving new SQT/DTA file info to database')
                return 'Error saving new SQT/DTA file info to database'

        session['dataset_id'] = dataset_id
        session['dbsearch_id'] = dbsearch_id
        session['ms1_data_ids'] = ms1_data_ids
        session['ms2_data_ids'] = ms2_data_ids
        session['sqt_data_ids'] = sqt_data_ids
        session['dta_data_ids'] = dta_data_ids

        return redirect(url_for('data.upload_view'))

    return render_template('data/document_index.html', upload_form=upload_form, recent_five_datasets=recent_five_datasets)


@data.route('/uploadview')
def upload_view():
    ## convert this to an ajax response

    return '''Successfully uploaded files!
            <br>dataset_id: {}
            <br>dbsearch_id: {}
            <br>ms1_data_ids: {}
            <br>ms2_data_ids: {}
            <br>sqt_data_ids: {}
            <br>dta_data_ids: {}'''.format( session['dataset_id'], 
                                            session['dbsearch_id'], 
                                            session['ms1_data_ids'], 
                                            session['ms2_data_ids'],
                                            session['sqt_data_ids'],
                                            session['dta_data_ids']
                                            )

