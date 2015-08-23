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

## API/Blueprint:

@api.route('/json')
def json_api():

    sample_dictionary = {'name': 'sandip', 'height': 68}

    return jsonify(sample_dictionary)

## regular view functions for app

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/API_test')
def test_API():
    json_obj = views_helpers.get_json_response('api.json_api')
    json_obj = json.loads(json_obj)
    
    # example modifying new dict
    json_obj['new'] = 3
    
    return json.dumps(json_obj)

