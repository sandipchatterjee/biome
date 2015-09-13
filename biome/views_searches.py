#!/usr/bin/env python3

from flask import ( abort, 
                    Blueprint, 
                    current_app,
                    flash,  
                    jsonify, 
                    redirect, 
                    render_template, 
                    request, 
                    session, 
                    url_for, 
                    )
from werkzeug import secure_filename
from biome import ( api, 
                    app, 
                    celery, 
                    data, 
                    db, 
                    decorators, 
                    forms, 
                    models, 
                    search, 
                    tasks, 
                    views_helpers, 
                    )
from tempfile import mkstemp
from celery import group, chain, chord
# from celery.result import AsyncResult
import re
import json
import shutil
import decimal

@data.route('/<dataset_pk>/newsearch', methods=('GET', 'POST'))
def new_search(dataset_pk):
    
    ''' Perform a new database search
    '''

    current_dataset = models.Dataset.query.get_or_404(dataset_pk)
    ms2_files = current_dataset.ms2files.all()
    if not ms2_files:
        abort(404)

    params_form = forms.SearchParamsForm()

    if params_form.validate_on_submit():

        params = json.loads(json.dumps(dict(params_form.data.items()), default=lambda x: float(x) if isinstance(x, decimal.Decimal) else x))

        ##### clean and edit params #####
        params = views_helpers.clean_params(params)

        # Save new DBSearch record (including params_dict) in database
        new_dbsearch_id = views_helpers.save_new_dbsearch(dataset_pk, params=params)

        params['dbsearch_id'] = new_dbsearch_id

        remote_host = 'admin@wolanlab'
        remote_filepaths = [ms2file.file_path for ms2file in ms2_files]


        # hard-coded for now... remove later! (once on production server)
        remote_filepaths = ['/home/admin/test_files/121614_SC_sampleH1sol_25ug_pepstd_HCD_FTMS_MS2_07_11.ms2', 
                            '/home/admin/test_files/121614_SC_sampleH1sol_25ug_pepstd_HCD_FTMS_MS2_07_11_duplicate.ms2']
        ###### REMOVE ^^

        rsync_task = tasks.rsync_file.s(remote_host, remote_filepaths, new_local_directory=None).set(queue='sandip')
        split_and_create_jobs_task = tasks.split_ms2_and_make_jobs.s(params).set(queue='sandip')

        launch_submission_tasks = tasks.launch_submission_tasks.s().set(queue='sandip')
        chained_tasks = rsync_task | split_and_create_jobs_task | launch_submission_tasks
        task = chained_tasks.apply_async()

        # save task ID to local database
        current_dbsearch = models.DBSearch.query.get(new_dbsearch_id)
        current_dbsearch.celery_id = str(task)
        current_dbsearch.status = 'submitted'
        db.session.commit()

        print(task.children) # this GroupResult ID won't be available until a few moments after launching

        app.logger.info('Launched Celery task {}'.format(task))

        return jsonify(params)

    return render_template( 'data/newsearch.html', 
                            params_form=params_form, 
                            current_dataset=current_dataset, 
                            ms2_files=ms2_files, 
                            )

@search.route('/')
def view_dbsearches():

    ''' View all DBSearch records
    '''

    # in the future, can limit this to only searches in progress
    all_dbsearches = models.DBSearch.query.order_by(models.DBSearch.start_time.desc()).all()
    parent_datasets = [models.Dataset.query.get(dbsearch.dataset_id) for dbsearch in all_dbsearches]

    return render_template( 'search/dbsearch_index.html', 
                            dbsearches_datasets=zip(all_dbsearches, parent_datasets), 
                            )


@search.route('/<dbsearch_pk>/', methods=('GET', 'POST'))
def view_dbsearch(dbsearch_pk):

    ''' View DBSearch
    '''

    current_dbsearch = models.DBSearch.query.get_or_404(dbsearch_pk)
    parent_dataset = models.Dataset.query.get_or_404(current_dbsearch.dataset_id)
    if current_dbsearch.celery_id:
        celery_task_obj = celery.AsyncResult(current_dbsearch.celery_id)
    else:
        celery_task_obj = None

    return render_template( 'search/dbsearch.html', 
                            current_dbsearch=current_dbsearch, 
                            parent_dataset=parent_dataset, 
                            celery_task_obj=celery_task_obj, 
                            )
