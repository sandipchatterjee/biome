#!/usr/bin/env python3

import json
from flask import ( Blueprint, 
                    current_app, 
                    jsonify, 
                    render_template, 
                    request, 
                    )
from biome import ( app, 
                    api, 
                    data, 
                    db, 
                    models, 
                    parsers,  
                    views_documents, 
                    views_helpers, 
                    views_plots, 
                    )

@api.route('/dataset/<dataset_pk>')
def dataset_quickinfo(dataset_pk):

    ''' Returns JSON object with some basic information about
        a dataset object with id=dataset_pk (used for "Quick View" link)
    '''

    dataset_object = models.Dataset.query.get(dataset_pk)

    if not dataset_object: # if dataset_object doesn't exist
        return jsonify({})

    dbsearch_ids = [dbsearch.id for dbsearch in dataset_object.dbsearches.all()]


    info_dict = { 'name': dataset_object.name, 
                    'id': dataset_object.id, 
                    'description': dataset_object.description, 
                    'ms1_files': [ms1file.id for ms1file in dataset_object.ms1files.all()], 
                    'ms2_files': [ms2file.id for ms2file in dataset_object.ms2files.all()], 
                    'dbsearches': dbsearch_ids,
                    }

    return jsonify(info_dict)

@api.route('/dta/<dtafile_id>')
def dtafile_quickinfo(dtafile_id):

    ''' Returns JSON object with information about a DTAFile
        record (with id=dtafile_id)
    '''

    dtafile_object = models.DTAFile.query.get(dtafile_id)

    if not dtafile_object:
        return jsonify({})

    info_dict = {   'id': dtafile_object.id, 
                    'file_name': dtafile_object.original_filename, 
                    'parent_dbsearch': dtafile_object.dbsearch_id, 
                    'created_time': str(dtafile_object.created_time), 
                    'flags': dtafile_object.flags, 
                    'deleted': dtafile_object.deleted, 
                    }

    return jsonify(info_dict)

@api.route('/sqt/<sqtfile_id>')
def sqtfile_quickinfo(sqtfile_id):

    ''' Returns JSON object with information about an SQTFile
        record (with id=sqtfile_id)
    '''

    sqtfile_object = models.SQTFile.query.get(sqtfile_id)

    if not sqtfile_object:
        return jsonify({})

    info_dict = {   'id': sqtfile_object.id, 
                    'file_name': sqtfile_object.original_filename, 
                    'parent_dbsearch': sqtfile_object.dbsearch_id, 
                    'created_time': str(sqtfile_object.created_time), 
                    'deleted': sqtfile_object.deleted, 
                    'scans': sqtfile_object.scans, 
                    }

    return jsonify(info_dict)

@api.route('/dta/<dtafile_id>.json')
def dtafile_json(dtafile_id):

    ''' Returns JSON object containing parsed DTASelect-filter.txt file
        (from DTAFile database record with id=dtafile_id)
    '''

    dtafile_object = models.DTAFile.query.get(dtafile_id)

    if not dtafile_object:
        return jsonify({})

    parsed = list(parsers.dtaselect_json(dtafile_object.file_path))

    # jsonify() allow top-level arrays... http://flask.pocoo.org/docs/0.10/security/#json-security
    return jsonify({'data':parsed})