#!/usr/bin/env python3

# some useful helper functions for biome.views
from flask import ( current_app,
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