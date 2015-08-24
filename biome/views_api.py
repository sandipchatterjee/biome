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