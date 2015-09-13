#!/usr/bin/env python3

# some useful helper functions for biome.views
from flask import ( current_app,
                    )
from biome import ( api, 
                    app, 
                    db, 
                    decorators, 
                    models, 
                    tasks, 
                    )
from hashlib import sha224

def get_json_response(view_name, *args, **kwargs):

    """ Get JSON response from view and return decoded JSON string.
        Can be parsed by calling function using JSON.loads(json_obj)
    """

    view = current_app.view_functions[view_name]
    resp = view(*args, **kwargs)

    json_obj = resp.get_data().decode('utf-8')
    
    return json_obj

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

def get_recent_records(model_obj, creation_time_field, n=5):

    ''' Returns the most recent n records (default of 5) from
        database table specified by model_obj (e.g., models.Dataset)
        and ordered by (descending) creation_time_field (e.g., models.Dataset.uploaded_time)
    '''

    return model_obj.query.filter_by(deleted=False).order_by(creation_time_field.desc()).limit(n).all()

@decorators.async
def count_scans_in_file(pk, filetype):

    ''' Counts scans in a recently uploaded MS2 or SQT file.

        Creates a new thread so that it doesn't hold up page loads.

        (in the future, will expand functionality to parse out other information upon file upload)
    '''

    if filetype == 'ms2':
        model_obj = models.MS2File.query.get(pk)
    elif filetype == 'sqt':
        model_obj = models.SQTFile.query.get(pk)
    else:
        app.logger.error('Invalid filetype "{}" given to count_scans_in_file()'.format(filetype))
        return

    with open(model_obj.file_path) as f:
        scan_count = len([line for line in f.readlines() if line.startswith('S\t')])

    model_obj.scans = scan_count

    db.session.commit()

    app.logger.info('Recorded {} scans in new MS2File ID {}'.format(scan_count, pk))

    return

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

    count_scans_in_file(new_ms2_file.id, 'ms2')

    app.logger.info('Saved new MS2 file {} (Dataset ID {}) to database'.format(file_path, dataset_id))

    return new_ms2_file.id

def save_new_sqt_record(dbsearch_id, file_path, original_filename=None):

    ''' Creates a new row in the sqt_file db table
    '''

    new_sqt_file = models.SQTFile(file_path, dbsearch_id, original_filename=original_filename)
    db.session.add(new_sqt_file)
    db.session.commit()

    app.logger.info('Saved new SQT file {} (Dataset ID {}) to database'.format(file_path, dbsearch_id))

    return new_sqt_file.id

def save_new_dta_record(dbsearch_id, file_path, original_filename=None):

    ''' Creates a new row in the dta_file db table
    '''

    # parse DTA file for 'flags' field... (something like '-p 2 -m 0 --trypstat')

    new_dta_file = models.DTAFile(file_path, dbsearch_id, original_filename=original_filename)
    db.session.add(new_dta_file)
    db.session.commit()

    app.logger.info('Saved new DTA file {} (Dataset ID {}) to database'.format(file_path, dbsearch_id))

    return new_dta_file.id