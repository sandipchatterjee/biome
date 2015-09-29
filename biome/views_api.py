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
                    tasks, 
                    views_documents, 
                    views_helpers, 
                    views_plots, 
                    )

@api.route('/mongos_status', methods=['GET', 'POST'])
def mongos_status():

    ''' API view for checking mongos status with a test query
        (see biome_worker.check_mongos_status for details)

        GET request: return jsonified information from database table

        POST request: launch remote task to check mongos statuses on cluster
    '''

    # look up mongos names from database here:
    mongos_hostnames = []

    # hard-coded for now:
    mongos_hostnames = ('imsb0501:27018', 
                        'imsb0515:27018', 
                        'imsb0601:27018', 
                        'imsb0615:27018', 
                        'node0097:27018', 
                        'node0113:27018', 
                        'node0129:27018', 
                        'node0145:27018', 
                        'node0401:27018', 
                        'node0411:27018', 
                        'node0421:27018', 
                        'node0431:27018', 
                        'node0441:27018', 
                        'node0451:27018', 
                        'node0461:27018', 
                        'node0471:27018', 
                        'node0481:27018', 
                        'node0491:27018', 
                        'node0501:27018', 
                        'node0511:27018', 
                        'node0521:27018', 
                        'node0531:27018', 
                        'node0541:27018', 
                        'node0551:27018', 
                        'node0561:27018', 
                        'node0571:27018', 
                        'node0581:27018', 
                        'node0591:27018', 
                        'node0601:27018', 
                        'node0617:27018', 
                        'node0633:27018', 
                        'node0649:27018', 
                        'node0665:27018', 
                        'node0681:27018', 
                        'node0922:27018', 
                        'node0937:27018', 
                        'node0953:27018', 
                        'node0969:27018', 
                        'node0985:27018', 
                        'node1001:27018', 
                        'nodea1301:27018',  
                        'nodea1331:27018',  
                        'nodea1401:27018',  
                        'nodea1431:27018',  
                        )

    if request.method == 'POST':

        task_id = tasks.check_mongos_status.apply_async(queue='sandip', 
                                                        args=[  mongos_hostnames, 
                                                                'MassDB_072114', 
                                                                'MassDB_072114'])
        return jsonify({'task_id': str(task_id)})
    else:
        return jsonify({'mongos_hostname1': 100, 'mongos_hostname2': 300})

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