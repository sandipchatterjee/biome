#!/usr/bin/env python3

# some useful helper functions for biome.views
from flask import ( current_app,
                    )
from biome import ( api, 
                    app, 
                    db, 
                    decorators, 
                    models, 
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