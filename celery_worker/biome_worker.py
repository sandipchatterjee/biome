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
    temp_dir_path = dir_name+'/'+temp_folder
    out_path = os.path.join(dir_name, temp_folder, base_name.replace('.ms2','_{#}.ms2'))
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

@app.task(name='biome_worker.split_ms2_and_make_jobs')
def split_ms2_and_make_jobs(new_local_directory, params_dict):

    ''' splits all ms2 files in new_local_directory
        and creates matched job files for each MS2 chunk
    '''

    MS2_files = glob.glob(new_local_directory+'/*.ms2')
    print('Splitting MS2 files: {}'.format(', '.join(MS2_files)))

    all_chunk_file_paths = []

    for file_path in MS2_files:
        all_chunk_file_paths.extend(split_ms2_file(file_path, params_dict))

    print(all_chunk_file_paths)

    return all_chunk_file_paths

@app.task(name='biome_worker.launch_submission_tasks')
def launch_submission_tasks(ms2_file_chunks):
    submission_tasks = group(submit_and_check_job.s(ms2_chunk).set(queue='sandip') for ms2_chunk in ms2_file_chunks)
    submission_tasks.apply_async()
    return submission_tasks

@app.task(bind=True, name='biome_worker.submit_and_check_job', max_retries = 20)
def submit_and_check_job(self, args):
    def resubmit():
        try:
            raise self.retry(countdown = randint(1,20))
        except MaxRetriesExceededError:
            print('Job failed exceeded max_retry')
            return 'Job failed exceeded max_retry'

    # fake logic for job failing ~50% of the time
    failure = True if randint(0, 1) else False
    if failure:
        resubmit()
    else:
        print('job succeeded -- {}'.format(args))
        return 'job succeeded -- {}'.format(args)

