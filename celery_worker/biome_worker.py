#!/usr/bin/env python3

# Launch Celery worker on remote host using a command like: 
# $ celery -A biome_worker worker --loglevel=info --queue sandip

import os
import sys
import glob
import time
import traceback
import subprocess
from celery import Celery, group
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

@app.task(name='biome_worker.rsync_file')
def rsync_file(remote_host, remote_filepaths, new_local_directory=None):

    ''' uses rsync to transfer files in list remote_filepaths from remote_host
        to local directory 'new_local_directory' (random hash generated if None)
    '''

    if not new_local_directory:
        new_local_directory = 'hashed_named_directory'
    new_local_directory = os.path.expanduser('~')+'/'+new_local_directory

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

@app.task(bind=True, name='biome_worker.submit_and_check_job', max_retries = 2)
def submit_and_check_job(self, args):
    def resubmit():
        try:
            raise self.retry(countdown = randint(1,20))
        except MaxRetriesExceededError:
            print('Job failed exceeded max_retry')
            raise # will also change task.status to FAILURE
            return 'Job failed exceeded max_retry'

    # fake logic for job failing ~50% of the time
    failure = True if randint(0, 1) else False
    if failure:
        resubmit()
    else:
        print('job succeeded -- {}'.format(args))
        return 'job succeeded -- {}'.format(args)

