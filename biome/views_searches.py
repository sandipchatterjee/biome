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
from uuid import uuid4
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
        if 'production' not in app.config['CONFIG_CLASS']:
            remote_filepaths = ['/home/admin/test_files/121614_SC_sampleH1sol_25ug_pepstd_HCD_FTMS_MS2_07_11.ms2', 
                                '/home/admin/test_files/121614_SC_sampleH1sol_25ug_pepstd_HCD_FTMS_MS2_07_11_duplicate.ms2']

        remote_directory = str(uuid4()) # random 36-character hash
        rsync_task = tasks.rsync_file.s(remote_host, remote_filepaths, new_local_directory=remote_directory).set(queue='sandip')
        split_and_create_jobs_task = tasks.split_ms2_and_make_jobs.s(params).set(queue='sandip')

        launch_submission_tasks = tasks.launch_submission_tasks.s().set(queue='sandip')
        chained_tasks = rsync_task | split_and_create_jobs_task | launch_submission_tasks
        task = chained_tasks.apply_async()

        # save task ID to local database
        current_dbsearch = models.DBSearch.query.get(new_dbsearch_id)
        current_dbsearch.celery_id = str(task)
        current_dbsearch.status = 'submitted'
        current_dbsearch.remote_directory = remote_directory
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

def set_or_update_celery_search_tasks(group_id, child_task_objects):

    ''' Sets or updates CelerySearchTask db table with current child task information

        - group_id a string equal to the celery group task ID (36-character hash)
        - child_task_objects is a list of Celery AsyncResult objects (child tasks of the group)
    '''

    try:
        for task_obj in child_task_objects:
            existing_record = models.CelerySearchTask.query.get(task_obj.id)
            if existing_record:
                if existing_record.status != task_obj.status:
                    existing_record.status = task_obj.status
                    db.session.add(existing_record)
            else:
                db.session.add(models.CelerySearchTask(group_id, task_obj.id, task_obj.status))
        else: # only commit to db if loop completed
            db.session.commit()
    except:
        app.logger.error('Error updating database -- trying to update CelerySearchTask(s) for Group ID {}'.format(group_id))
        raise
        return False

    return True

@search.route('/<dbsearch_pk>/resubmit', methods=('GET', 'POST'))
def resubmit_search_tasks(dbsearch_pk):

    ''' resubmits search tasks
    '''

    current_dbsearch = models.DBSearch.query.get(dbsearch_pk)
    remote_directory = current_dbsearch.remote_directory

    # get old Task ID from POST request
    old_child_task_id = request.form['oldTaskID']
    print(old_child_task_id)

    # resubmit job (launch remote celery task)
    job_file_path = None

    # Celery task: submit_and_check_job(self, job_file_path, job_id=None, old_task_info=None)
    # task.apply_async(args, kwargs) -- args is a list/tuple, kwargs is a dict

    new_task = tasks.submit_and_check_job.apply_async((job_file_path, ), dict(old_task_info=(remote_directory, old_child_task_id)), queue='sandip')
    new_task_id = str(new_task)

    # update dbsearch.status
    current_dbsearch.status = 'resubmitted'

    # update CelerySearchTask table 
    celery_subtask_row = models.CelerySearchTask.query.get(old_child_task_id)
    celery_subtask_row.child_task_id = new_task_id
    celery_subtask_row.status = 'RETRY'

    db.session.add(current_dbsearch)
    db.session.add(celery_subtask_row)
    db.session.commit()

    new_task_info = {   'new_id': celery_subtask_row.child_task_id, 
                        'old_id': old_child_task_id, 
                        'status': current_dbsearch.status, 
                        }

    return jsonify(new_task_info)

@search.route('/<dbsearch_pk>/', methods=('GET', 'POST'))
def view_dbsearch(dbsearch_pk):

    ''' View DBSearch
    '''

    current_dbsearch = models.DBSearch.query.get_or_404(dbsearch_pk)
    parent_dataset = models.Dataset.query.get_or_404(current_dbsearch.dataset_id)
    sqt_files = current_dbsearch.sqtfiles.all()
    dta_files = current_dbsearch.dtafiles.all()
    search_params = current_dbsearch.params

    # quick hack for mongodb_uri super long string param value...
    if search_params:
        for key in search_params:
            if len(str(search_params[key])) > 30:
                search_params[key] = search_params[key].replace(',', ', ')

    if current_dbsearch.celery_id and current_dbsearch.status:

        # if there is a Celery Group Task ID and overall status associated with this DBSearch
        #
        #   - these should have been set upon submitting a job)
        #   - if not set, this DBSearch was generated by uploading search files and not by 
        #     starting a new search of MS2 data (so don't show anything)

        if current_dbsearch.status == 'submitted':

            # overall dbsearch status should be set to 'submitted' immediately upon 
            # search form/job submission from the "New Proteomic Search" page
            #
            #  - check to see if Group ID has children
            #  - if group has child tasks, set/update CelerySearchTasks with task information
            #    and return statuses to page
            #  - if group has no child tasks, return 'search job submitted' status to page

            celery_task_obj = celery.AsyncResult(current_dbsearch.celery_id)

            if celery_task_obj.children:

                group_result = celery_task_obj.children[0]

                if set_or_update_celery_search_tasks(current_dbsearch.celery_id, group_result):
                    
                    # CelerySearchTask table update succeeded

                    celery_subtasks = current_dbsearch.celery_search_tasks.all()

                    # if all subtasks have successfully finished, update parent DBSearch.status
                    # and return template without any subtask information
                    # (FUTURE TODO: delete associated CelerySearchTask rows)

                    all_jobs_finished = all([subtask.status == 'SUCCESS' for subtask in celery_subtasks])

                    if all_jobs_finished:

                        current_dbsearch.status = 'search complete'
                        db.session.add(current_dbsearch)
                        db.session.commit()

                        return render_template( 'search/dbsearch.html', 
                                current_dbsearch=current_dbsearch, 
                                parent_dataset=parent_dataset, 
                                sqt_files=sqt_files, 
                                dta_files=dta_files, 
                                search_params=search_params, 
                                )
                    
                    grouped_subtasks = {'complete': [task for task in celery_subtasks if task.status == 'SUCCESS'], 
                                        'pending_retry': [task for task in celery_subtasks if task.status in ('PENDING', 'RETRY')], 
                                        'failed': [task for task in celery_subtasks if task.status == 'FAILURE']
                                        }

                    current_dbsearch.status = 'searching'
                    db.session.add(current_dbsearch)
                    db.session.commit()

                    return render_template( 'search/dbsearch.html', 
                                            current_dbsearch=current_dbsearch, 
                                            parent_dataset=parent_dataset, 
                                            sqt_files=sqt_files, 
                                            dta_files=dta_files, 
                                            search_params=search_params, 
                                            celery_subtasks=celery_subtasks, 
                                            grouped_subtasks=grouped_subtasks, 
                                            )
                else: 
                    # couldn't update CelerySearchTask table in database...
                    # (just leave current_dbsearch.status as 'submitted' and do nothing)
                    pass
            else:
                pass # report Task Submitted
        elif current_dbsearch.status == 'searching':

            # this means that Celery subtasks were found and stored in the CelerySearchTask db table

            # get current status and update db
            celery_task_obj = celery.AsyncResult(current_dbsearch.celery_id)
            group_result = celery_task_obj.children[0]
            if set_or_update_celery_search_tasks(current_dbsearch.celery_id, group_result):

                celery_subtasks = current_dbsearch.celery_search_tasks.all()

                # if all subtasks have successfully finished, update parent DBSearch.status
                # and return template without any subtask information
                # (FUTURE TODO: delete associated CelerySearchTask rows)

                all_jobs_finished = all([subtask.status == 'SUCCESS' for subtask in celery_subtasks])

                if all_jobs_finished:

                    current_dbsearch.status = 'search complete'
                    db.session.add(current_dbsearch)
                    db.session.commit()

                    return render_template( 'search/dbsearch.html', 
                            current_dbsearch=current_dbsearch, 
                            parent_dataset=parent_dataset, 
                            sqt_files=sqt_files, 
                            dta_files=dta_files, 
                            search_params=search_params, 
                            )

                grouped_subtasks = {'complete': [task for task in celery_subtasks if task.status == 'SUCCESS'], 
                                    'pending_retry': [task for task in celery_subtasks if task.status in ('PENDING', 'RETRY')], 
                                    'failed': [task for task in celery_subtasks if task.status == 'FAILURE']
                                    }

                return render_template( 'search/dbsearch.html', 
                                        current_dbsearch=current_dbsearch, 
                                        parent_dataset=parent_dataset, 
                                        sqt_files=sqt_files, 
                                        dta_files=dta_files, 
                                        search_params=search_params, 
                                        celery_subtasks=celery_subtasks, 
                                        grouped_subtasks=grouped_subtasks, 
                                        )

            else:
                # database update failed -- don't change status (do nothing)
                pass

        elif current_dbsearch.status == 'resubmitted':
            
            # Celery subtask IDs in database table assumed to be correct,
            # because some of the original tasks have been replaced by new tasks

            celery_subtasks = current_dbsearch.celery_search_tasks.all()

            # if all subtasks have successfully finished, update parent DBSearch.status
            # and return template without any subtask information
            # (FUTURE TODO: delete associated CelerySearchTask rows)

            all_jobs_finished = all([subtask.status == 'SUCCESS' for subtask in celery_subtasks])

            if all_jobs_finished:

                current_dbsearch.status = 'search complete'
                db.session.add(current_dbsearch)
                db.session.commit()

                return render_template( 'search/dbsearch.html', 
                        current_dbsearch=current_dbsearch, 
                        parent_dataset=parent_dataset, 
                        sqt_files=sqt_files, 
                        dta_files=dta_files, 
                        search_params=search_params, 
                        )

            # Only querying Celery backend for tasks that have 'FAILURE' status in database

            for subtask in celery_subtasks:
                if subtask.status != 'SUCCESS':
                    celery_task_obj = celery.AsyncResult(subtask.child_task_id)
                    subtask.status = celery_task_obj.status # this returns PENDING if the task ID doesn't exist in the Celery backend...
                    db.session.add(subtask)
            else:
                db.session.commit()

            # update celery_subtasks
            celery_subtasks = current_dbsearch.celery_search_tasks.all()
            grouped_subtasks = {'complete': [task for task in celery_subtasks if task.status == 'SUCCESS'], 
                                'pending_retry': [task for task in celery_subtasks if task.status in ('PENDING', 'RETRY')], 
                                'failed': [task for task in celery_subtasks if task.status == 'FAILURE']
                                }

            return render_template( 'search/dbsearch.html', 
                                    current_dbsearch=current_dbsearch, 
                                    parent_dataset=parent_dataset, 
                                    sqt_files=sqt_files, 
                                    dta_files=dta_files, 
                                    search_params=search_params, 
                                    celery_subtasks=celery_subtasks, 
                                    grouped_subtasks=grouped_subtasks, 
                                    )

        # elif current_dbsearch.status == 'search complete':

        #     # database search is complete; template should display an option for running DTASelect

        #     pass # should render template with default values here...

        else:

            # unknown value for current_dbsearch.status 
            # (do nothing -- return base template below)

            pass

    else:

        # (current_dbsearch.celery_id and current_dbsearch.status) returned False
        # Don't report anything about Celery search tasks (there isn't anything to report)

        pass


    return render_template( 'search/dbsearch.html', 
                            current_dbsearch=current_dbsearch, 
                            parent_dataset=parent_dataset, 
                            sqt_files=sqt_files, 
                            dta_files=dta_files, 
                            search_params=search_params, 
                            )

@search.route('/<dbsearch_pk>/submitdtaselect')
def submit_dtaselect(dbsearch_pk):

    ''' Submits combine_sqt_parts, make_filtered_fasta, 
        and run_dtaselect remote tasks in a Celery chain
    '''

    current_dbsearch = models.DBSearch.query.get(dbsearch_pk)
    base_directory_name = current_dbsearch.remote_directory
    params = current_dbsearch.params

    if current_dbsearch.status != 'search complete':
        return jsonify({'error': 'invalid status for filtering'})

    task_id = str(tasks.combine_sqt_parts.apply_async(args=[base_directory_name, params], queue='sandip'))

    combine_sqt_parts_task = tasks.combine_sqt_parts.s(base_directory_name, params).set(queue='sandip')
    make_filtered_fasta_task = tasks.make_filtered_fasta.s(params).set(queue='sandip')
    dtaselect_task = tasks.dtaselect_task.s(params).set(queue='sandip')

    # chained_tasks = combine_sqt_parts_task | make_filtered_fasta_task
    chained_tasks = combine_sqt_parts_task | make_filtered_fasta_task | dtaselect_task
    task_id = chained_tasks.apply_async()

    # update dbsearch celery_id and status
    # current_dbsearch.celery_id = str(task_id)
    current_dbsearch.status = 'running dtaselect'
    db.session.add(current_dbsearch)
    db.session.commit()

    return jsonify({'task_id': str(task_id)})

