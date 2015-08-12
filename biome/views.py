#!/usr/bin/env python3

import json
from flask import ( render_template, jsonify, 
                    Blueprint, current_app,
                    request
                )
from biome import app, api

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


## simple test with Bokeh -- from example on github: 
## https://github.com/bokeh/bokeh/tree/master/examples/embed/simple

from bokeh.embed import components
from bokeh.plotting import figure
from bokeh.resources import INLINE
from bokeh.templates import RESOURCES
from bokeh.util.string import encode_utf8

colors = {
    'Black': '#000000',
    'Red':   '#FF0000',
    'Green': '#00FF00',
    'Blue':  '#0000FF',
}


def getitem(obj, item, default):
    if item not in obj:
        return default
    else:
        return obj[item]

@app.route("/bokeh_test")
def polynomial():
    """ Very simple embedding of a polynomial chart"""
    # Grab the inputs arguments from the URL
    # This is automated by the button
    args = request.args

    # Get all the form arguments in the url with defaults
    color = colors[getitem(args, 'color', 'Black')]
    _from = int(getitem(args, '_from', 0))
    to = int(getitem(args, 'to', 10))

    # Create a polynomial line graph
    x = list(range(_from, to + 1))
    fig = figure(title="Polynomial")
    fig.line(x, [i ** 2 for i in x], color=color, line_width=2)

    # Configure resources to include BokehJS inline in the document.
    # For more details see:
    #   http://bokeh.pydata.org/en/latest/docs/reference/resources_embedding.html#module-bokeh.resources
    plot_resources = RESOURCES.render(
        js_raw=INLINE.js_raw,
        css_raw=INLINE.css_raw,
        js_files=INLINE.js_files,
        css_files=INLINE.css_files,
    )

    # For more details see:
    #   http://bokeh.pydata.org/en/latest/docs/user_guide/embedding.html#components
    script, div = components(fig, INLINE)
    html = render_template(
        'embed.html',
        plot_script=script, plot_div=div, plot_resources=plot_resources,
        color=color, _from=_from, to=to
    )
    return encode_utf8(html)
