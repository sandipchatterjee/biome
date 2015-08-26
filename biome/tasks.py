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