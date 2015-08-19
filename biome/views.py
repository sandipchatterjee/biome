#!/usr/bin/env python3

import json
from flask import ( render_template, jsonify, 
                    Blueprint, current_app,
                    request
                    )
from biome import ( app, api, 
                    data, views_plots, 
                    views_documents
                    )

## API/Blueprint:


@api.route('/json')
def json_api():

    sample_dictionary = {'name': 'sandip', 'height': 68}

    return jsonify(sample_dictionary)

## regular view functions for app

@app.route('/')
def index():
    return render_template('index.html')

def get_json_response(view_name, *args, **kwargs):

    """ Get JSON response from view and return decoded JSON string.
        Can be parsed by calling function using JSON.loads(json_obj)
    """

    view = current_app.view_functions[view_name]
    resp = view(*args, **kwargs)

    json_obj = resp.get_data().decode('utf-8')
    
    return json_obj

@app.route('/API_test')
def test_API():
    json_obj = get_json_response('api.json_api')
    json_obj = json.loads(json_obj)
    
    # example modifying new dict
    json_obj['new'] = 3
    
    return json.dumps(json_obj)


