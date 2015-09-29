#!/usr/bin/env python3

# Launch Celery worker on remote host using a command like: 
# $ celery -A biome_worker worker --loglevel=info --queue sandip

import os
import sys
import glob
import time
import timeit
import traceback
import subprocess
import make_filtered_fasta_helpers
from celery import Celery, group
from fileinput import FileInput
from random import randint
from textwrap import dedent
from celery.exceptions import MaxRetriesExceededError

try:
    # Not necessary for the user. Only on the worker
    import drmaa
except ImportError as exc:
    print(exc)
except RuntimeError as exc:
    # Could not find drmaa library
    print(exc)

try:
    import pymongo
except ImportError as exc
    print("Couldn't import pymongo... some tasks not functional")
    print(exc)

ex_path = os.path.split(os.path.abspath(__file__))[0] # the directory in which this script lives

app = Celery('biome')
app.config_from_object('celeryconfig')

@app.task(name='biome_worker.add')
def add(x, y):
    return x + y

@app.task(name='biome_worker.tsum')
def tsum(numbers):
    return sum(numbers)

@app.task(name='biome_worker.echo')
def echo(echo_string='hello world'):
    print(echo_string)
    return echo_string

@app.task(bind=True, name='biome_worker.rsync_file')
def rsync_file(self, remote_host, remote_filepaths, new_local_directory=None):

    ''' uses rsync to transfer files in list remote_filepaths from remote_host
        to local directory 'new_local_directory' (random hash generated if None)
    '''

    if not new_local_directory:
        new_local_directory = self.request.id
    new_local_directory = os.path.expanduser('~')+'/biome_proteomics/data/'+new_local_directory

    if os.path.exists(new_local_directory):
        pass # should probably exit or at least throw a warning
    else:
        os.makedirs(new_local_directory)

    args = ['rsync', '-av', 
            '{}:{}'.format(remote_host, remote_filepaths[0])]
    if remote_filepaths[1:]:
        args = args+[':'+filepath for filepath in remote_filepaths[1:]]
    args.append('{}/'.format(new_local_directory))

    stdout = subprocess.check_output(args)

    print(stdout)
    return new_local_directory

def split_ms2_file(ms2_file_path, params_dict):

    ''' Splits an MS2 file (ms2_file_path) into split_n subfiles 
        by scan (lines that match '^S\t')

        Returns a list of new subfile absolute paths

        ** Requires GNU grep to be available as `grep` on worker **
        ** Requires GNU parallel to be available as `parallel` on worker **
    '''

    split_n = params_dict['split_n']
    temp_folder = params_dict['temp']

    print('Splitting: ' + ms2_file_path)
    dir_name = os.path.dirname(ms2_file_path)
    base_name = os.path.basename(ms2_file_path)
    temp_dir_path = os.path.join(dir_name, temp_folder)
    out_path = os.path.join(temp_dir_path, base_name.replace('.ms2','_{#}.ms2'))
    if not os.path.exists(temp_dir_path):
        os.makedirs(temp_dir_path)

    num_scans = int(subprocess.check_output(['grep', '-c', '^S', ms2_file_path]))
    block_size = round(num_scans / split_n) + 1
    
    command = "cat {ms2_file_path} | parallel --pipe -N {block_size} --recstart 'S\\t' \"cat > {out_path} && echo {out_path}\"".format(
    **{'ms2_file_path': ms2_file_path, 'block_size': block_size, 'out_path': out_path})
    
    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if p.returncode != 0:
         raise ValueError(stderr)
    return stdout.decode('utf-8').splitlines()

def make_job_file(ms2_chunk_file, params_dict):

    ''' Makes a PBS job file for an input MS2_chunk_file
        based on user-specified parameters in params_dict
    '''

    dir_name = os.path.dirname(ms2_chunk_file)
    base_name = os.path.basename(ms2_chunk_file)
    file_name = base_name.split('.')[0]
    job_file_path = ms2_chunk_file.replace('.ms2','.job')
    
    job_boilerplate = '\n'.join((   '#!/bin/bash',
                                    '#PBS -l nodes=1:ppn={}'.format(params_dict['numcores']),
                                    '#PBS -l cput={}:00:00'.format(params_dict['cputime']),
                                    '#PBS -l walltime={}:00:00'.format(params_dict['walltime']),
                                    '#PBS -j oe',
                                    '#PBS -l mem={}gb'.format(params_dict['memgb']),
                                    '#PBS -N "BM_{}"'.format(file_name),
                                    '#PBS -o {}'.format(ms2_chunk_file.replace('.ms2','.$PBS_JOBID')),
                                    '#PBS -m n', # suppress job-related status emails from PBS admin
                                    ))

    customization_dict = {  'num_threads': params_dict['numthreads'], 
                            'blazmass_jar': params_dict['blazmass_jar'], 
                            'ms2_file': ms2_chunk_file, 
                            'base_name': base_name, 
                            'job_file': job_file_path, 
                            # 'ex_path': params_dict['ex_path'],
                            'dir_name': dir_name, 
                            }
                    
    base_job_file_not_sharded = dedent("""
                    echo "################################################################################"
                    echo "Processing MS2 file: {ms2_file}"
                    echo "PBS job script file: {job_file}"
                    echo "Running on node: `hostname`"
                    echo "################################################################################"
                    
                    module load java/1.7.0_21
                    cd {dir_name}
                    echo $PBS_JOBID >> ../job.ids
                    java -jar {blazmass_jar} . {base_name} blazmass.params {num_threads}
                    STATUS=$?
                    if [ $STATUS -ne 0 ]; then
                      echo "Blazmass failed"; exit $STATUS
                    else
                      echo "Finished Successfully!"
                    fi

                    """).format(**customization_dict)
    
    with open(job_file_path, 'w') as f:
        print('Writing job file: ' + job_file_path)
        f.write(job_boilerplate + '\n' + base_job_file_not_sharded)
        
    return job_file_path

def make_blazmass_params(temp_dir, params_dict):

    ''' Make custom blazmass.params file from template using params_dict '''

    bm_params_template = os.path.join(ex_path, 'blazmass.params.template')
    bm_params_out = os.path.join(temp_dir, 'blazmass.params')
    bm_params_text = open(bm_params_template).read().format(**params_dict)
    with open(bm_params_out, 'w') as f:
        f.write(bm_params_text)
    return bm_params_out

@app.task(name='biome_worker.split_ms2_and_make_jobs')
def split_ms2_and_make_jobs(new_local_directory, params_dict):

    ''' Splits all ms2 files in new_local_directory
        and creates matched job files for each MS2 chunk

        Returns a list of all PBS job file absolute paths
        (one job file per MS2 chunk)
    '''

    MS2_files = glob.glob(new_local_directory+'/*.ms2')
    temp_dir_path = os.path.join(new_local_directory, params_dict['temp'])

    print('Splitting MS2 files: {}'.format(', '.join(MS2_files)))

    all_chunk_file_paths = []

    for file_path in MS2_files:
        all_chunk_file_paths.extend(split_ms2_file(file_path, params_dict))

    job_file_paths = [make_job_file(ms2_chunk_file, params_dict) for ms2_chunk_file in all_chunk_file_paths]
    blazmass_params_path = make_blazmass_params(temp_dir_path, params_dict)

    print(job_file_paths)

    return job_file_paths

@app.task(name='biome_worker.launch_submission_tasks')
def launch_submission_tasks(job_file_paths):
    submission_tasks = group(submit_and_check_job.s(job_file).set(queue='sandip') for job_file in job_file_paths)
    submission_tasks.apply_async()
    return submission_tasks

def submit_pbs_job(job_file_path):

    ''' Submits a job specified by job_path to the PBS cluster
        queue using `qsub` and returns PBS job ID (string)
    '''

    submit_command = ['qsub', job_file_path]

    try:
        job_id = subprocess.check_output(submit_command).decode('utf-8').strip()
        return job_id
    except subprocess.CalledProcessError:
        return None

def check_job_output(job_file_path, job_id):

    ''' Run several quick tests to see if a job 
        that completed "successfully" actually 
        finished properly
    '''

    ms2_file_path = job_file_path.replace('.job', '.ms2')
    sqt_file_path = job_file_path.replace('.job', '.sqt')
    job_log_file_path = job_file_path.replace('.job', '.'+job_id)

    # make sure SQT file exists and has nonzero size
    try:
        sqt_has_nonzero_size = os.path.getsize(sqt_file_path)
    except FileNotFoundError:
        sqt_has_nonzero_size = False

    # make sure job_log_file_path (job log) exists
    # make sure 'INFO: Done processing MS2:' is in job_log file
    try:
        done_processing_ms2 = subprocess.check_output(['grep', '-q', 'INFO: Done processing MS2:', job_log_file_path])
        done_processing_ms2 = True # necessary because grep -q returns an empty string...
    except subprocess.CalledProcessError:
        # file doesn't exist or grep could not find search string in log file
        # (nonzero exit code)
        done_processing_ms2 = False

    # make sure SQT output has >= 95% as many scans as MS2 input
    # (scans could still have no matches...)
    try:
        ms2_scans = int(subprocess.check_output(['grep', '-c', '^S', ms2_file_path]))
        sqt_scans = int(subprocess.check_output(['grep', '-c', '^S', sqt_file_path]))
        if sqt_scans >= ms2_scans*0.5:
            enough_scans = True
        else:
            enough_scans = False
    except subprocess.CalledProcessError:
        # one of the files not found... or some other error with grep
        # (or... zero scans found in one of the files)
        enough_scans = False

    return all((sqt_has_nonzero_size, 
                done_processing_ms2, 
                enough_scans, 
                ))

@app.task(bind=True, name='biome_worker.submit_and_check_job', max_retries = 3)
def submit_and_check_job(self, job_file_path, job_id=None, old_task_info=None, dta_task=False):

    ''' Submits using submit_pbs_job() and checks PBS job status (using drmaa)
        for proteomic search jobs

        PBS jobs are wrapped in this Celery task. Celery's retry functionality is used
        with the drmaa module to check job status
    '''

    def resubmit():
        try:
            raise self.retry((job_file_path,), {'job_id': None, 'dta_task':dta_task}, countdown = randint(1,20))
        except MaxRetriesExceededError:
            print('Job failed exceeded max_retry')
            raise # will also change task.status to FAILURE
            return 'Job failed exceeded max_retry'

    if old_task_info:
        # this task is being manually resubmitted by the user
        group_id, old_child_task = old_task_info

        base_data_directory = os.path.expanduser('~')+'/biome_proteomics/data'
        group_id_data_directory = base_data_directory+'/'+group_id
        old_task_id_file = group_id_data_directory+'/dummy/'+old_child_task+'.taskid'
        with open(old_task_id_file) as f:
            job_file_path = f.read().strip()

    if job_id is None:
        # PBS job not yet submitted, or job submission failed

        # save qsub arguments to file (filename = [celery task id].taskid) -- might use this for resubmission
        working_directory = os.path.dirname(job_file_path)
        task_id_args_path = os.path.join(working_directory, self.request.id+'.taskid')
        with open(task_id_args_path, 'w') as f:
            f.write(job_file_path)

        job_id = submit_pbs_job(job_file_path)
        print('PBS Job ID: {}'.format(job_id))

    with drmaa.Session() as s:
        job_status = s.jobStatus(job_id)
    print('PBS Job Status: {}'.format(job_status))

    if job_status not in ('done', 'failed'):
        # job is either queued, active, or on hold -- check again in 30-90 seconds

        # don't count this status check as a celery task.retry attempt:
        self.request.retries -= 1

        raise self.retry((job_file_path,), {'job_id': job_id, 'dta_task':dta_task}, countdown = randint(30,60))

    elif job_status == 'failed':
        # unknown PBS job failure
        resubmit()

    else:
        # job_status == 'done'

        if dta_task:
            return 'Job succeeded: {}'.format(job_file_path)
        else:
            # check job file for correct # of scans, check output for 'INFO: Done processing MS2:', etc.
            # (if that fails, resubmit())
            if check_job_output(job_file_path, job_id):
                return 'Job succeeded: {}'.format(job_file_path)
            else:
                print('Job {} completed but failed tests'.format(job_file_path))
                resubmit()

@app.task(name='biome_worker.combine_sqt_parts')
def combine_sqt_parts(base_directory_name, params):

    ''' Combines all SQT subparts (from cluster search) 
        into their parent files
    '''

    base_directory = os.path.join(  os.path.expanduser('~'),
                                    'biome_proteomics',
                                    'data',
                                    base_directory_name
                                    )
    os.chdir(base_directory)
    temp_directory_name = params['temp']
    temp_directory = os.path.join(  base_directory,
                                    temp_directory_name
                                    )

    # get parent MS2 filenames
    # i.e., 121614_SC_sampleH1sol_25ug_pepstd_HCD_FTMS_MS2_07.ms2
    base_ms2_files = [os.path.basename(filepath) for filepath in glob.glob(os.path.join(base_directory, '*.ms2'))]

    # extract base names
    # i.e., '121614_SC_sampleH1sol_25ug_pepstd_HCD_FTMS_MS2_07'
    base_filenames = [filename.replace('.ms2', '') for filename in base_ms2_files]

    for base_filename in base_filenames:
        child_files = glob.glob(os.path.join(temp_directory, base_filename+'*.sqt'))

        if child_files:

            # Save "H" lines at the start of the file
            with open(child_files[0]) as f:
                H_lines = []
                for line in f:
                    if line.startswith('H\t'):
                        H_lines.append(line)
                    else:
                        break

            # Create a new base SQT file with H_lines and all other data from child files
            with open(base_filename+'.sqt', 'w') as f, FileInput(child_files) as g:
                for line in H_lines:
                    f.write(line)
                for line in g:
                    if not line.startswith('H\t'):
                        if line.endswith('\n'):
                            f.write(line)
                        else:
                            f.write(line+'\n')

    return base_directory

@app.task(name='biome_worker.make_filtered_fasta')
def make_filtered_fasta(base_directory, params):

    ''' Make a filtered FASTA file for DTASelect
    '''

    if make_filtered_fasta_helpers.run( mongodb_uri=params['mongodb_uri'], 
                                        seqdb_name=params['seqdb_name'], 
                                        seqdbcoll=params['seqdbcoll'], 
                                        protdb_name=params['protdb_name'], 
                                        protdbcoll=params['protdbcoll'], 
                                        sequest=True, 
                                        cwd=base_directory, 
                                        ):
        print('Filtered FASTA file created successfully')

    return base_directory

def make_dta_job_file(base_directory, dta_params):

    ''' Makes a PBS job file for running 
        DTASelect (uses dta_params to customize)

        if successful, returns new job file path
    '''

    job_boilerplate = '\n'.join((   '#!/bin/bash',
                                    '#PBS -l nodes=1:ppn={}'.format(8),
                                    '#PBS -l cput={}:00:00'.format(192),
                                    '#PBS -l walltime={}:00:00'.format(24),
                                    '#PBS -j oe',
                                    '#PBS -l mem={}gb'.format(dta_params['memgb']),
                                    '#PBS -N "BM_DTASelect"', 
                                    '#PBS -m n', # suppress job-related status emails from PBS admin
                                    ))
                    
    base_job_file = dedent("""
                    echo "################################################################################"
                    echo "Running DTASelect at {base_directory}"
                    echo "Running on node: `hostname`"
                    echo "################################################################################"
                    
                    module load java/1.7.0_21
                    cd {base_directory}
                    echo $PBS_JOBID > ../dtajob.id
                    java -Xmx{memgb}G -cp {dtaselect_classpath} DTASelect --quiet --brief --sfp {sfp} -p {ppp} > dtaselect.out
                    STATUS=$?
                    if [ $STATUS -ne 0 ]; then
                      echo "DTASelect failed"; exit $STATUS
                    else
                      echo "Finished Successfully!"
                    fi

                    """).format(**dta_params)
    job_file_path = os.path.join(base_directory, 'dtaselect.job')
    with open(job_file_path, 'w') as f:
        print('Writing job file: ' + job_file_path)
        f.write(job_boilerplate + '\n' + base_job_file)

    return job_file_path


@app.task(name='biome_worker.dtaselect_task')
def dtaselect_task(base_directory, params):

    ''' Submit DTASelect job and monitor status using submit_and_check_job
    '''

    os.chdir(base_directory)

    dta_params = {  'memgb': 24, 
                    'dtaselect_classpath': params['dtaselect_classpath'], 
                    'base_directory': base_directory, 
                    'sfp': params['sfp'], 
                    'ppp': params['ppp'], 
                    }

    job_file_path = make_dta_job_file(base_directory, dta_params)

    new_submit_and_check_job = submit_and_check_job.apply_async(args=(job_file_path,), 
                                                                kwargs=dict(dta_task=True), 
                                                                queue='sandip', 
                                                                )

    return new_submit_and_check_job

@app.task(name='biome_worker.check_mongos_status')
def check_mongos_status(mongos_hostnames, massdb_name, massdbcoll):

    ''' Checks mongos connection status for each hostname in
        mongos_hostnames, which is a list of strings formatted like:
        ['node1234:27018', 'node3456:27018', ...]

        Performs a small query on MongoDB database 'massdb_name.massdbcoll'

        Returns a dict of query times (in milliseconds): 
        {'mongos_hostname1':query_time_ms, 'mongos_hostname2':query_time_ms, ...}
    '''

    time_dict = {}
    setup_command_string = "from pymongo import MongoClient; db=MongoClient('mongodb://{mongodb_hostname}', socketTimeoutMS = 10*1000, connectTimeoutMS = 10*1000, serverSelectionTimeoutMS = 10*1000)['{massdb_name}']['{massdbcoll}']"
    query_command_string = "list(db.find({'$and':[{'_id':{'$gte':1000000}}, {'_id':{'$lte':1000500}}]}))"
    number_of_repeats = 3

    for mongos_hostname in mongos_hostnames:
        try:
            query_time = timeit.timeit( query_command_string, 
                                        number=number_of_repeats, 
                                        setup=setup_command_string.format(**dict(   massdb_name=massdb_name, 
                                                                                    massdbcoll=massdbcoll, 
                                                                                    mongodb_hostname=mongos_hostname)))
            time_dict[mongos_hostname] = int((query_time/number_of_repeats)*1000) # convert to integer milliseconds
        except (pymongo.errors.ServerSelectionTimeoutError, pymongo.errors.ExecutionTimeout):
            time_dict[mongos_hostname] = -1
        except pymongo.errors.ConnectionFailure:
            time_dict[mongos_hostname] = -2

    return time_dict