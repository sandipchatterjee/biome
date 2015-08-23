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
                    views_helpers, 
                    )
from tempfile import mkstemp
import re
import json
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

def save_new_file(file_obj):

    ''' Saves a new file (specified by file_obj) to new_file_path by calculating
        its SHA224 hash and saving as 'SHA224_digest.[file_extension]'

        Returns new_file_path for new saved file.
    '''

    uploads_dir = app.config['UPLOAD_FOLDER']+'/'
    tmp_file_path = mkstemp()[1]
    file_obj.save(tmp_file_path)
    hash_val = views_helpers.get_hash(tmp_file_path)

    original_filename = secure_filename(file_obj.filename)

    new_file_path = uploads_dir+hash_val+original_filename[-4:]
    shutil.move(tmp_file_path, new_file_path)

    app.logger.info('Saved uploaded file {} to {}'.format(file_obj.filename, new_file_path))

    return new_file_path, original_filename

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

def save_new_ms1_record(dataset_id, file_path, original_filename=None):

    ''' Creates a new row in the ms1_file db table
    '''

    new_ms1_file = models.MS1File(file_path, dataset_id, original_filename=original_filename)
    db.session.add(new_ms1_file)
    db.session.commit()

    app.logger.info('Saved new MS1 file {} (Dataset ID {}) to database'.format(file_path, dataset_id))

    return new_ms1_file.id

def save_new_ms2_record(dataset_id, file_path, original_filename=None):

    ''' Creates a new row in the ms2_file db table
    '''

    new_ms2_file = models.MS2File(file_path, dataset_id, original_filename=original_filename)
    db.session.add(new_ms2_file)
    db.session.commit()

    app.logger.info('Saved new MS2 file {} (Dataset ID {}) to database'.format(file_path, dataset_id))

    return new_ms2_file.id

def save_new_dta_record(dbsearch_id, file_path, original_filename=None):

    ''' Creates a new row in the dta_file db table
    '''

    # parse DTA file for 'flags' field... (something like '-p 2 -m 0 --trypstat')

    new_dta_file = models.DTAFile(file_path, dbsearch_id, original_filename=original_filename)
    db.session.add(new_dta_file)
    db.session.commit()

    app.logger.info('Saved new DTA file {} (Dataset ID {}) to database'.format(file_path, dbsearch_id))

    return new_dta_file.id

def save_new_sqt_record(dbsearch_id, file_path, original_filename=None):

    ''' Creates a new row in the sqt_file db table
    '''

    new_sqt_file = models.SQTFile(file_path, dbsearch_id, original_filename=original_filename)
    db.session.add(new_sqt_file)
    db.session.commit()

    app.logger.info('Saved new SQT file {} (Dataset ID {}) to database'.format(file_path, dbsearch_id))

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

@data.route('/', methods=('GET', 'POST'))
def document_index():

    ''' View function for "index" page for all document types (including file uploader interface)
    '''

    upload_form = SubmitForm()

    recent_five_datasets = views_helpers.get_recent_records(models.Dataset, models.Dataset.uploaded_time)

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
        ms1_data_ids = None
        ms2_data_ids = None
        sqt_data_ids = None
        dta_data_ids = None

        # save new dataset in database
        dataset_name = upload_form.dataset_name.data
        dataset_description = upload_form.dataset_desc.data
        try:
            dataset_id = save_new_dataset(dataset_name, dataset_description)
        except:
            app.logger.error('Error creating new dataset {}'.format(dataset_name))
            raise
            return None

        if ms1_file_paths:
            try:
                # save MS1 records to database
                ms1_data_ids = [save_new_ms1_record(dataset_id, ms1_file_path, original_filename) for ms1_file_path, original_filename in ms1_file_paths]
            except:
                # log database error and return
                app.logger.error('Error saving new MS1 file info to database')
                raise
                return None

        if ms2_file_paths:
            try:
                # save MS2 records to database
                ms2_data_ids = [save_new_ms2_record(dataset_id, ms2_file_path, original_filename) for ms2_file_path, original_filename in ms2_file_paths]
            except:
                # log database error and return
                app.logger.error('Error saving new MS2 file info to database')
                raise
                return None

        if sqt_file_paths or dta_file_paths:
            try:
                dbsearch_id = save_new_dbsearch(dataset_id) # create DBSearch
            except:
                # log DB error and return
                app.logger.error('Error saving new Database Search to database')
                raise
                return None
            if sqt_file_paths:                
                try:
                    # save SQT records to database
                    sqt_data_ids = [save_new_sqt_record(dbsearch_id, sqt_file_path, original_filename) for sqt_file_path, original_filename in sqt_file_paths]
                except:
                    app.logger.error('Error saving new SQT file info to database')
                    raise
                    return None
            if dta_file_paths:
                try:
                    # save DTA records to database
                    dta_data_ids = [save_new_dta_record(dbsearch_id, dta_file_path, original_filename) for dta_file_path, original_filename in dta_file_paths]
                except:
                    app.logger.error('Error saving new DTA file info to database')
                    raise
                    return None

        return jsonify({'dataset_id': dataset_id, 
                        'dataset_name': dataset_name, 
                        'dataset_description': dataset_description, 
                        'dbsearch_id': dbsearch_id,
                        'ms1_data_ids': ms1_data_ids,
                        'ms2_data_ids': ms2_data_ids, 
                        'sqt_data_ids': sqt_data_ids, 
                        'dta_data_ids': dta_data_ids, 
                        })

    return render_template('data/document_index.html', upload_form=upload_form, recent_five_datasets=recent_five_datasets)

@data.route('/<dataset_pk>/quickview')
def dataset_quickinfo(dataset_pk):

    ''' Returns JSON object with some basic information about
        a dataset object with id=dataset_pk (used for "Quick View" link)
    '''

    dataset_object = models.Dataset.query.get(dataset_pk)
    dbsearch_ids = [dbsearch.id for dbsearch in dataset_object.dbsearches.all()]

    info_dict = { 'name': dataset_object.name, 
                    'id': dataset_object.id, 
                    'description': dataset_object.description, 
                    'ms1_files': [ms1file.id for ms1file in dataset_object.ms1files.all()], 
                    'ms2_files': [ms2file.id for ms2file in dataset_object.ms2files.all()], 
                    'dbsearches': dbsearch_ids,
                    }

    return jsonify(info_dict)

@data.route('/<dataset_pk>', methods=('GET', 'POST'))
def dataset_info(dataset_pk):

    ''' View function that displays information about a 
        Dataset with id=dataset_pk

        Looks up associated files via associated tables.

        Allows editing/deleting of associated files (or entire dataset)
    '''

    current_dataset = models.Dataset.query.get(dataset_pk)

    # this is performing a second identical DB query... not ideal:
    dataset_quickinfo_dict = views_helpers.get_json_response('data.dataset_quickinfo', dataset_pk)
    dataset_quickinfo_dict = json.loads(dataset_quickinfo_dict)

    return render_template('data/dataset.html', dataset_id=dataset_pk, current_dataset=current_dataset, dataset_quickinfo_dict=dataset_quickinfo_dict)

@data.route('/<dataset_pk>/delete')
def delete_dataset(dataset_pk):

    ''' "Deletes" dataset (id=dataset_pk) by setting Dataset.deleted=True

        "Recovers" dataset if url is accessed with argument recover=True like this:
        /<dataset_pk>/delete?recover=True
    '''

    # new_status flag sets [model_instance].deleted to True or False
    # depending on whether it should be "deleted" or "recovered"
    new_status = not request.args.get('recover', None)

    dataset_quickinfo_dict = views_helpers.get_json_response('data.dataset_quickinfo', dataset_pk)
    dataset_quickinfo_dict = json.loads(dataset_quickinfo_dict)

    # "delete" dataset
    current_dataset = models.Dataset.query.get(dataset_pk)
    current_dataset.deleted = new_status

    # "delete" associated MS1 and MS2 files
    for ms1_file_id in dataset_quickinfo_dict['ms1_files']:
        ms1_file = models.MS1File.query.get(ms1_file_id)
        ms1_file.deleted = new_status

    for ms2_file_id in dataset_quickinfo_dict['ms2_files']:
        ms2_file = models.MS2File.query.get(ms2_file_id)
        ms2_file.deleted = new_status

    # "delete" associated dbsearches
    if dataset_quickinfo_dict['dbsearches']:
        all_sqt_files = []
        all_dta_files = []

        for dbsearch_pk in dataset_quickinfo_dict['dbsearches']:
            current_dbsearch = models.DBSearch.query.get(dbsearch_pk)
            current_dbsearch.deleted = new_status

            for sqt_file in current_dbsearch.sqtfiles.all():
                all_sqt_files.append(sqt_file)

            for dta_file in current_dbsearch.dtafiles.all():
                all_dta_files.append(dta_file)

        # "delete" associated SQT and DTA files
        for sqt_file in all_sqt_files:
            sqt_file.deleted = new_status

        for dta_file in all_dta_files:
            dta_file.deleted = new_status

    db.session.commit()

    app.logger.info('Deleted Dataset "{}" (Dataset ID {}) and associated files from database'.format(current_dataset.name, current_dataset.id))

    return redirect(url_for('data.document_index')) # pass a message here confirming delete

@data.route('/search/<dbsearch_pk>', methods=('GET', 'POST'))
def dbsearch_info(dbsearch_pk):

    return ''

@data.route('/ms1/<ms1file_pk>', methods=('GET', 'POST'))
def ms1file_info(ms1file_pk):

    return ''

@data.route('/ms2/<ms2file_pk>', methods=('GET', 'POST'))
def ms2file_info(ms2file_pk):

    return ''

@data.route('/sqt/<sqtfile_pk>', methods=('GET', 'POST'))
def sqtfile_info(sqtfile_pk):

    return ''

@data.route('/dta/<dtafile_pk>', methods=('GET', 'POST'))
def dtafile_info(dtafile_pk):

    return ''

