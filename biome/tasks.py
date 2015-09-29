#!/usr/bin/env python3

from biome import ( app, 
                    celery, 
                    db, 
                    models, 
                    )


import time
@celery.task
def celery_background_task(arg1, arg2):

    ''' Sample Celery background task
    '''

    print('sleeping for 15 seconds')
    print(app.config['CELERY_BROKER_URL'])
    time.sleep(15)
    print('waking up')

    return arg1+arg2

@celery.task(name='biome_worker.echo', queue='sandip')
def echo(echo_string="hello"):

    ''' For testing out remote Celery worker 
    '''

    pass

@celery.task(name='biome_worker.add', queue='sandip')
def add(x, y):

    ''' For testing out remote Celery worker 
    '''

    pass

@celery.task(name='biome_worker.tsum', queue='sandip')
def tsum(x, y):

    ''' For testing out remote Celery worker 
    '''

    pass

# @celery.task(name='biome_worker.rsync_file', queue='sandip')
# def rsync_file(remote_host, remote_filepaths, new_local_directory=None):
@celery.task(bind=True, name='biome_worker.rsync_file')
def rsync_file(self, remote_host, remote_filepaths, new_local_directory=None):
    pass

@celery.task(name='biome_worker.split_ms2_and_make_jobs', queue='sandip')
def split_ms2_and_make_jobs(new_local_directory, params_dict):
    pass

@celery.task(bind=True, name='biome_worker.submit_and_check_job', max_retries=3)
def submit_and_check_job(self, job_file_path, job_id=None, old_task_info=None, dta_task=False):
    pass

@celery.task(name='biome_worker.launch_submission_tasks')
def launch_submission_tasks(ms2_file_chunks):
    pass

@celery.task(name='biome_worker.combine_sqt_parts')
def combine_sqt_parts(base_directory_name, params):
    pass

@celery.task(name='biome_worker.make_filtered_fasta')
def make_filtered_fasta(base_directory, params):
    pass

@celery.task(name='biome_worker.dtaselect_task')
def dtaselect_task(base_directory, params):
    pass

@celery.task(name='biome_worker.check_mongos_status')
def check_mongos_status(mongos_hostnames, massdb_name, massdbcoll):
    pass