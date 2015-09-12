
from datetime import timedelta

BROKER_URL = 'redis://wl-cmadmin:6379/0'
CELERY_RESULT_BACKEND = 'redis://wl-cmadmin:6379'

CELERY_TASK_SERIALIZER = 'pickle'
CELERY_RESULT_SERIALIZER = 'pickle'
CELERY_ACCEPT_CONTENT=['pickle']
CELERY_TIMEZONE = 'America/Los_Angeles'

CELERY_TASK_RESULT_EXPIRES = 14 * 24 * 60 * 60 #seconds
BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 1 * 24 * 60 * 60}

CELERYBEAT_SCHEDULE = {
    'check-mongos': {
        'task': 'submit_blazmass_worker.check_mongos_status',
        'schedule': timedelta(minutes=20),
        'args': ("wl-cmadmin", 27018, 'MassDB_072114', 'MassDB_072114'),
        'options': {'queue' : 'submit_bm'}
    },
}

