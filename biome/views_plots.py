#!/usr/bin/env python3

import numpy as np
import json
from flask import ( render_template, jsonify,
                    Blueprint, current_app,
                    request
                    )
from biome import ( app, 
                    api, 
                    data, 
                    models, 
                    views_helpers, 
                    )

from collections import Counter

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


@data.route('/dta/<dtafile_pk>/saltstep')
def salt_step_peptide_analysis(dtafile_pk):

    ''' Determines how many filtered peptides are present 
        per chromatography step and draws a plot
    '''

    current_dtafile = models.DTAFile.query.get_or_404(dtafile_pk)

    dtafile_quickinfo_dict = views_helpers.get_json_response('api.dtafile_quickinfo', dtafile_pk)
    dtafile_quickinfo_dict = json.loads(dtafile_quickinfo_dict)

    dtafile_json = views_helpers.get_json_response('api.dtafile_json', dtafile_pk)
    dtafile_json = json.loads(dtafile_json)

    parent_dbsearch = models.DBSearch.query.get_or_404(dtafile_quickinfo_dict['parent_dbsearch'])
    sqt_files = parent_dbsearch.sqtfiles.all()
    parent_dataset = models.Dataset.query.get_or_404(parent_dbsearch.dataset_id)

    def get_distinct_psm_ids(dtaselect_parser):
        psms = set()
        for locus in dtaselect_parser:
            for peptide in locus['peptides']:
                psm_id = str(peptide['LCStep'])+'_'+str(peptide['Scan'])+'_'+str(peptide['ChargeState'])
                psms.add(psm_id)
        return psms

    def make_LCStep_histogram(psm_ids_set):
        full_lcstep_count = []
        for psm in psm_ids_set:
            full_lcstep_count.append(psm.split('_')[0])

        return Counter(full_lcstep_count)

    psm_ids = get_distinct_psm_ids(dtafile_json['data'])
    hist = make_LCStep_histogram(psm_ids)
    labels, values = zip(*sorted(hist.items(), key=lambda x: int(x[0])))
    labels = np.array(labels)
    values = np.array(values)

    fig = figure(title="Peptides per LC Step", y_range=[0, max(values)*1.25], plot_height=400, plot_width=700)
    fig.rect(x=labels, y=values/2, width=0.8, height=values)
    fig.xaxis.axis_label = 'chromatography step'
    fig.yaxis.axis_label = '# peptides identified'
    from bokeh.models import FixedTicker
    fig.xaxis[0].ticker.desired_num_ticks = len(labels)

    plot_resources = RESOURCES.render(
        js_raw=INLINE.js_raw,
        css_raw=INLINE.css_raw,
        js_files=INLINE.js_files,
        css_files=INLINE.css_files,
    )

    script, div = components(fig, INLINE)

    return render_template( 'plots/empty.html', 
                            dtafile_quickinfo_dict=dtafile_quickinfo_dict, 
                            current_dtafile=current_dtafile, 
                            parent_dbsearch=parent_dbsearch, 
                            sqt_files=sqt_files, 
                            parent_dataset=parent_dataset, 
                            plot_script=script, 
                            plot_div=div, 
                            plot_resources=plot_resources, 
                            # color=color, 
                            # _from=_from, 
                            # to=to, 
                            )