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
                    data, 
                    db, 
                    decorators, 
                    forms, 
                    models, 
                    tasks, 
                    views_helpers, 
                    )
from tempfile import mkstemp
from celery import group, chain, chord
import re
import json
import shutil
import decimal

file_types = [  ('MS2', 'MS2'),
                ('DTA', 'DTA'),
                ('SQT', 'SQT'),
                ('MS1', 'MS1')
            ]
file_extensions = ('ms2', 'sqt', 'txt', 'ms1')

def save_new_file(file_obj):

    ''' Saves a new file (specified by file_obj) to new_file_path by calculating
        its SHA224 hash and saving as 'SHA224_digest.[file_extension]'

        Returns new_file_path for new saved file.
    '''

    uploads_dir = app.config['UPLOAD_FOLDER']+'/'
    tmp_file_path = mkstemp()[1]
    file_obj.save(tmp_file_path)
    hash_val = views_helpers.get_hash(tmp_file_path)

    original_filename = secure_filename(file_obj.filename)

    new_file_path = uploads_dir+hash_val+original_filename[-4:]
    shutil.move(tmp_file_path, new_file_path)

    app.logger.info('Saved uploaded file {} to {}'.format(file_obj.filename, new_file_path))

    return new_file_path, original_filename

def check_file_types(filename_list):

    ''' Checks incoming files for correct file extensions
        and file names. Returns True if all OK, False if not.
    '''

    accepted_file_extensions = {'ms2',
                                'sqt',
                                'txt', # DTASelect-filter.txt
                                'ms1',
                                }

    # check to make sure all filenames end in a correct extension
    if not all([filename[-3:].lower() in accepted_file_extensions for filename in filename_list]):
        return False

    # check to make sure all '.txt' files also end with 'DTASelect-filter.txt'
    potential_dta_files = [filename for filename in filename_list if filename.endswith('.txt')]
    if not all([re.search(r'^.*DTASelect-filter.txt$', filename) for filename in potential_dta_files]):
        return False

    return True

@data.route('/', methods=('GET', 'POST'))
def document_index():

    ''' View function for "index" page for all document types (including file uploader interface)
    '''

    upload_form = forms.DatasetUploadForm()

    recent_five_datasets = views_helpers.get_recent_records(models.Dataset, models.Dataset.uploaded_time)

    if upload_form.validate_on_submit():

        files = request.files.getlist('data_file')
        filenames = [file_obj.filename for file_obj in files]
        app.logger.info('User trying to upload files {}'.format(', '.join(filenames)))

        if not check_file_types(filenames):
            return 'Can\'t upload all of those file types... {}'.format(', '.join(filenames)) # this should return a redirect to a different view/AJAX response

        # save new uploaded file data
        try:
            ms1_file_paths = [save_new_file(file_obj) for file_obj in files if file_obj.filename.endswith('.ms1')]
            ms2_file_paths = [save_new_file(file_obj) for file_obj in files if file_obj.filename.endswith('.ms2')]
            sqt_file_paths = [save_new_file(file_obj) for file_obj in files if file_obj.filename.endswith('.sqt')]
            dta_file_paths = [save_new_file(file_obj) for file_obj in files if file_obj.filename.endswith('.txt')]
        except:
            app.logger.error('Error saving new files')
            return 'Error saving new files'

        dataset_id = None
        dbsearch_id = None
        ms1_data_ids = None
        ms2_data_ids = None
        sqt_data_ids = None
        dta_data_ids = None

        # save new dataset in database
        dataset_name = upload_form.dataset_name.data
        dataset_description = upload_form.dataset_desc.data
        try:
            dataset_id = views_helpers.save_new_dataset(dataset_name, dataset_description)
        except:
            app.logger.error('Error creating new dataset {}'.format(dataset_name))
            raise
            return None

        if ms1_file_paths:
            try:
                # save MS1 records to database
                ms1_data_ids = [views_helpers.save_new_ms1_record(dataset_id, ms1_file_path, original_filename) for ms1_file_path, original_filename in ms1_file_paths]
            except:
                # log database error and return
                app.logger.error('Error saving new MS1 file info to database')
                raise
                return None

        if ms2_file_paths:
            try:
                # save MS2 records to database
                ms2_data_ids = [views_helpers.save_new_ms2_record(dataset_id, ms2_file_path, original_filename) for ms2_file_path, original_filename in ms2_file_paths]
            except:
                # log database error and return
                app.logger.error('Error saving new MS2 file info to database')
                raise
                return None

        if sqt_file_paths or dta_file_paths:
            try:
                dbsearch_id = views_helpers.save_new_dbsearch(dataset_id) # create DBSearch
            except:
                # log DB error and return
                app.logger.error('Error saving new Database Search to database')
                raise
                return None
            if sqt_file_paths:                
                try:
                    # save SQT records to database
                    sqt_data_ids = [views_helpers.save_new_sqt_record(dbsearch_id, sqt_file_path, original_filename) for sqt_file_path, original_filename in sqt_file_paths]
                    for sqt_data_id in sqt_data_ids:
                        views_helpers.count_scans_in_file(sqt_data_id, 'sqt')
                except:
                    app.logger.error('Error saving new SQT file info to database')
                    raise
                    return None
            if dta_file_paths:
                try:
                    # save DTA records to database
                    dta_data_ids = [views_helpers.save_new_dta_record(dbsearch_id, dta_file_path, original_filename) for dta_file_path, original_filename in dta_file_paths]
                except:
                    app.logger.error('Error saving new DTA file info to database')
                    raise
                    return None

        return jsonify({'dataset_id': dataset_id, 
                        'dataset_name': dataset_name, 
                        'dataset_description': dataset_description, 
                        'dbsearch_id': dbsearch_id,
                        'ms1_data_ids': ms1_data_ids,
                        'ms2_data_ids': ms2_data_ids, 
                        'sqt_data_ids': sqt_data_ids, 
                        'dta_data_ids': dta_data_ids, 
                        })

    return render_template('data/document_index.html', upload_form=upload_form, recent_five_datasets=recent_five_datasets)

@data.route('/<dataset_pk>', methods=('GET', 'POST'))
def dataset_info(dataset_pk):

    ''' View function that displays information about a 
        Dataset with id=dataset_pk

        Looks up associated files via associated tables.

        Allows editing/deleting of associated files (or entire dataset)
    '''

    current_dataset = models.Dataset.query.get_or_404(dataset_pk)

    # this is performing a second identical DB query... not ideal:
    dataset_quickinfo_dict = views_helpers.get_json_response('api.dataset_quickinfo', dataset_pk)
    dataset_quickinfo_dict = json.loads(dataset_quickinfo_dict)

    return render_template('data/dataset.html', dataset_id=dataset_pk, current_dataset=current_dataset, dataset_quickinfo_dict=dataset_quickinfo_dict)

@data.route('/dta/<dtafile_pk>', methods=('GET', 'POST'))
def dtafile_info(dtafile_pk):

    ''' View function that displays information about a 
        DTAFile with id=dtafile_pk

        Looks up associated files via associated tables.

        Allows editing/deleting of associated files (or entire dataset)
    '''

    current_dtafile = models.DTAFile.query.get_or_404(dtafile_pk)

    # this is performing a second identical DB query... not ideal:
    dtafile_quickinfo_dict = views_helpers.get_json_response('api.dtafile_quickinfo', dtafile_pk)
    dtafile_quickinfo_dict = json.loads(dtafile_quickinfo_dict)

    parent_dbsearch = models.DBSearch.query.get_or_404(dtafile_quickinfo_dict['parent_dbsearch'])
    sqt_files = parent_dbsearch.sqtfiles.all()
    parent_dataset = models.Dataset.query.get_or_404(parent_dbsearch.dataset_id)

    return render_template( 'data/dtafile.html', 
                            current_dtafile=current_dtafile, 
                            parent_dbsearch=parent_dbsearch, 
                            sqt_files=sqt_files, 
                            parent_dataset=parent_dataset, 
                            dtafile_quickinfo_dict=dtafile_quickinfo_dict)

@data.route('/dta', methods=('GET', 'POST'))
def dtafile_index():

    ''' List view for all DTASelect files
        (all rows in DTAFile relation)
    '''

    show_all = request.args.get('recover', False)

    all_dta_files = models.DTAFile.query.filter_by(deleted=show_all).order_by(models.DTAFile.created_time.desc()).all()
    
    # probably really inefficient...
    all_dta_files_parents = [models.Dataset.query.get(models.DBSearch.query.get(dta_file.dbsearch_id).dataset_id) for dta_file in all_dta_files]

    return render_template('data/dtafile_index.html', all_dta_files=zip(all_dta_files, all_dta_files_parents))

@data.route('/<dataset_pk>/delete')
def delete_dataset(dataset_pk):

    ''' "Deletes" dataset (id=dataset_pk) by setting Dataset.deleted=True

        "Recovers" dataset if url is accessed with argument recover=True like this:
        /<dataset_pk>/delete?recover=True
    '''

    # new_status flag sets [model_instance].deleted to True or False
    # depending on whether it should be "deleted" or "recovered"
    new_status = not request.args.get('recover', None)

    dataset_quickinfo_dict = views_helpers.get_json_response('api.dataset_quickinfo', dataset_pk)
    dataset_quickinfo_dict = json.loads(dataset_quickinfo_dict)

    # "delete" dataset
    current_dataset = models.Dataset.query.get(dataset_pk)
    current_dataset.deleted = new_status

    # "delete" associated MS1 and MS2 files
    for ms1_file_id in dataset_quickinfo_dict['ms1_files']:
        ms1_file = models.MS1File.query.get(ms1_file_id)
        ms1_file.deleted = new_status

    for ms2_file_id in dataset_quickinfo_dict['ms2_files']:
        ms2_file = models.MS2File.query.get(ms2_file_id)
        ms2_file.deleted = new_status

    # "delete" associated dbsearches
    if dataset_quickinfo_dict['dbsearches']:
        all_sqt_files = []
        all_dta_files = []

        for dbsearch_pk in dataset_quickinfo_dict['dbsearches']:
            current_dbsearch = models.DBSearch.query.get(dbsearch_pk)
            current_dbsearch.deleted = new_status

            for sqt_file in current_dbsearch.sqtfiles.all():
                all_sqt_files.append(sqt_file)

            for dta_file in current_dbsearch.dtafiles.all():
                all_dta_files.append(dta_file)

        # "delete" associated SQT and DTA files
        for sqt_file in all_sqt_files:
            sqt_file.deleted = new_status

        for dta_file in all_dta_files:
            dta_file.deleted = new_status

    db.session.commit()

    app.logger.info('Deleted Dataset "{}" (Dataset ID {}) and associated files from database'.format(current_dataset.name, current_dataset.id))

    return redirect(url_for('data.document_index')) # pass a message here confirming delete

@data.route('/dta/<dtafile_pk>/delete')
def delete_dtafile(dtafile_pk):

    new_status = not request.args.get('recover', None)

    current_dtafile = models.DTAFile.query.get(dtafile_pk)
    current_dtafile.deleted = new_status

    db.session.commit()

    return redirect(url_for('data.dtafile_index')) # pass a message here confirming delete

@data.route('/search/<dbsearch_pk>', methods=('GET', 'POST'))
def dbsearch_info(dbsearch_pk):

    return ''

@data.route('/ms1/<ms1file_pk>', methods=('GET', 'POST'))
def ms1file_info(ms1file_pk):

    return ''

@data.route('/ms2/<ms2file_pk>', methods=('GET', 'POST'))
def ms2file_info(ms2file_pk):

    return ''

@data.route('/sqt/<sqtfile_pk>', methods=('GET', 'POST'))
def sqtfile_info(sqtfile_pk):

    ''' View function that displays information about a 
        SQTFile with id=sqtfile_pk

        Looks up associated files via associated tables.

        Allows editing/deleting of associated files (or entire dataset)
    '''

    current_sqtfile = models.SQTFile.query.get_or_404(sqtfile_pk)

    # this is performing a second identical DB query... not ideal:
    sqtfile_quickinfo_dict = views_helpers.get_json_response('api.sqtfile_quickinfo', sqtfile_pk)
    sqtfile_quickinfo_dict = json.loads(sqtfile_quickinfo_dict)

    parent_dbsearch = models.DBSearch.query.get_or_404(sqtfile_quickinfo_dict['parent_dbsearch'])
    dta_files = parent_dbsearch.dtafiles.all()
    parent_dataset = models.Dataset.query.get_or_404(parent_dbsearch.dataset_id)

    return render_template( 'data/sqtfile.html', 
                            current_sqtfile=current_sqtfile, 
                            parent_dbsearch=parent_dbsearch, 
                            dta_files=dta_files, 
                            parent_dataset=parent_dataset, 
                            sqtfile_quickinfo_dict=sqtfile_quickinfo_dict)

@data.route('/sqt', methods=('GET', 'POST'))
def sqtfile_index():

    ''' List view for all SQT files
        (all rows in SQTFile relation)
    '''

    show_all = request.args.get('recover', False)

    all_sqt_files = models.SQTFile.query.filter_by(deleted=show_all).order_by(models.SQTFile.created_time.desc()).all()
    
    # probably really inefficient...
    all_sqt_files_parents = [models.Dataset.query.get(models.DBSearch.query.get(sqt_file.dbsearch_id).dataset_id) for sqt_file in all_sqt_files]

    return render_template('data/sqtfile_index.html', all_sqt_files=zip(all_sqt_files, all_sqt_files_parents))

@data.route('/sqt/<sqtfile_pk>/delete')
def delete_sqtfile(sqtfile_pk):
    # will integrate this into delete_dtafile (to make one universal "delete one file" view instead of duplicating code)
    return 'not implemented yet' 

@data.route('/launchtask')
def launch_task():

    ''' Sample view that launches a celery async task. Only used for testing.
    '''

    # WORKING!!
    # callback = tasks.tsum.s().set(queue='sandip')
    # header = [tasks.add.s(i,i) for i in range(8)]
    # result = chord(header)(callback)

    # WORKING!!
    # callback = tasks.tsum.si([-1,-2]).set(queue='sandip') # '.si' method ignores all previous group callback methods
    # header = [tasks.add.s(i,i).set(queue='sandip') for i in range(800)]
    # result = chord(header)(callback)

    # task = tasks.echo.apply_async(args=['hello world'], queue='sandip')
    # job = chord([   tasks.echo.s('hello'), 
    #                 tasks.echo.s('hi'), 
    #                 tasks.echo.s({'dict':'contentss', 'key': 2}), 
    #                 tasks.echo.s('helloagain')], tasks.echo.si('lastone'))

    # WORKING!!
    # callback = tasks.echo.si('all done!').set(queue='sandip') # '.si' method ignores all previous group callback methods
    # task_group = [task_obj.set(queue='sandip') for task_obj in (tasks.echo.s('hello'), 
    #                                                             tasks.echo.s('hi'), 
    #                                                             tasks.echo.s({'dict':'contentss', 'key': 2}), 
    #                                                             tasks.echo.s('helloagain')
    #                                                             )]
    # result = chord(task_group)(callback)

    # WORKING!!
    # callback = tasks.echo.si('all done!').set(queue='sandip') # '.si' method ignores all previous group callback methods
    # task_group = [task_obj.set(queue='sandip') for task_obj in (tasks.echo.s('hello'), 
    #                                                             tasks.echo.s('hi'), 
    #                                                             tasks.echo.s({'dict':'contentss', 'key': 2}), 
    #                                                             tasks.echo.s('helloagain')
    #                                                             )]
    # result = group(task_group) | callback
    # result.apply_async()

    # WORKING!!
    # callback = tasks.echo.si('all done!').set(queue='sandip') # '.si' method ignores all previous group callback methods
    # task_group = [task_obj.set(queue='sandip') for task_obj in (tasks.echo.s('hello'), 
    #                                                             tasks.echo.s('hi'), 
    #                                                             tasks.echo.s({'dict':'contentss', 'key': 2}), 
    #                                                             tasks.echo.s('helloagain')
    #                                                             )]
    # task_group2 = [task_obj.set(queue='sandip') for task_obj in (tasks.echo.si('hello'), 
    #                                                             tasks.echo.si('hi'), 
    #                                                             tasks.echo.si({'dict':'contentss', 'key': 2}), 
    #                                                             tasks.echo.si('helloagain')
    #                                                             )]*4
    # result = group(task_group) | callback
    # result.apply_async() # this may still be running when second set is started
    # result2 = group(task_group2) | callback
    # result2.apply_async()

    # this will be hardcoded for our purposes -- or, in production, using socket.gethostname()
    remote_host = 'admin@wolanlab'

    # this will be retrieved from the MS2File db table
    remote_filepaths = ['/home/admin/test_files/121614_SC_sampleH1sol_25ug_pepstd_HCD_FTMS_MS2_07_11.ms2', 
                        '/home/admin/test_files/121614_SC_sampleH1sol_25ug_pepstd_HCD_FTMS_MS2_07_11_duplicate.ms2']

    # hardcoded for now, but params_dict will be retrieved from DBSearch.params field
    params_dict = {'split_n': 5}

    # last_group_of_tasks = group([tasks.submit_and_check_job.si('useless_arg').set(queue='sandip')]*25)
    # last_group_of_tasks = group([tasks.submit_and_check_job.s().set(queue='sandip')]*25)

    # chained_tasks = rsync_task | split_and_create_jobs_task | last_group_of_tasks

    rsync_task = tasks.rsync_file.s(remote_host, remote_filepaths, new_local_directory=None).set(queue='sandip')
    split_and_create_jobs_task = tasks.split_ms2_and_make_jobs.s(params_dict).set(queue='sandip')

    launch_submission_tasks = tasks.launch_submission_tasks.s().set(queue='sandip')
    chained_tasks = rsync_task | split_and_create_jobs_task | launch_submission_tasks
    task = chained_tasks.apply_async()

    print(task.children) # this GroupResult ID won't be available until a few moments after launching

    app.logger.info('Launched Celery task {}'.format(task))

    return 'Launched!'

def clean_params(params):

    ''' Cleans and fills in missing/misformatted search parameters
    '''

    if params['server_preset'] not in ('garibaldi', 'ims'):
        params['server_preset'] = 'garibaldi'

    if params['server_preset'] == 'ims':
        params['mongodb_uri'] = 'mongodb://imsb0501:27018,imsb0515:27018,imsb0601:27018,imsb0615:27018'


    # number of threads to run Blazmass using (should be <= num_cores)
    if params['numthreads'] > params['numcores']:
        params['numthreads'] = params['numcores']

    # cputime and memgb cannot be user-specified (not part of form)
    params['cputime'] = params['walltime'] * params['numthreads']
    params['memgb'] = round(params['numthreads'] * 1.5)  # allowing 1.5GB RAM per thread

    # convert certain params from boolean to 1 or 0
    params['use_protdb'] = 1 if params['use_protdb'] else 0
    params['use_seqdb'] = 1 if params['use_seqdb'] else 0
    params['ppm_fragment_ion_tolerance_high'] = 1 if params['ppm_fragment_ion_tolerance_high'] else 0

    # this can be cleaned up...
    if not ('diff_search_options' in params and len(params['diff_search_options'])>1):
        params['diff_search_options'] = ''
    if not ('diff_search_Nterm' in params and len(params['diff_search_Nterm'])>1):
        params['diff_search_Nterm'] = ''
    if not ('diff_search_Cterm' in params and len(params['diff_search_Cterm'])>1):
        params['diff_search_Cterm'] = ''

    if not ('reverse_peptides' in params and len(params['reverse_peptides'])>1):
        params['reverse_peptides'] = 0
    else:
        params['reverse_peptides'] = 1 if params['reverse_peptides'] else 0
    
    params['job_spacing'] = params.get('job_spacing', 1/60)
    params['job_spacing_init'] = params.get('job_spacing_init', 0)

    return params

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
        params = clean_params(params)

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

