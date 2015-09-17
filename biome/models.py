#!/usr/bin/env python3

from biome import ( app, 
                    db,
                    )
from sqlalchemy.dialects import postgresql
from datetime import datetime

class Dataset(db.Model):

    ''' Represents a related collection of datafiles (MS1, MS2)
    '''

    __tablename__ = 'dataset'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60))
    description = db.Column(db.String(500))
    uploaded_time = db.Column(db.DateTime)
    deleted = db.Column(db.Boolean)
    dbsearches = db.relationship('DBSearch', backref='parent_dataset', lazy='dynamic')
    ms1files = db.relationship('MS1File', backref='parent_dataset', lazy='dynamic')
    ms2files = db.relationship('MS2File', backref='parent_dataset', lazy='dynamic')

    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.deleted = False # never actually delete information... just set flag to True
        self.uploaded_time = datetime.now()

    def __repr__(self):
        return '<Dataset ID: {}>'.format(self.name)

class DBSearch(db.Model):

    ''' Represents a Blazmass/ComPIL Search.
        Associated with a single Dataset.
    '''

    __tablename__ = 'db_search'

    id = db.Column(db.Integer, primary_key=True)
    params = db.Column(postgresql.JSON)
    start_time = db.Column(db.DateTime)

    celery_id = db.Column(db.String(36), unique=True) # Celery Task ID (group task ID -- see CelerySearchTask)
    status = db.Column(db.String(25))

    deleted = db.Column(db.Boolean)

    dataset_id = db.Column(db.Integer, db.ForeignKey('dataset.id'))

    sqtfiles = db.relationship('SQTFile', backref='dbsearch', lazy='dynamic')
    dtafiles = db.relationship('DTAFile', backref='dbsearch', lazy='dynamic')
    celery_search_tasks = db.relationship('CelerySearchTask', backref='dbsearch', lazy='dynamic')

    def __init__(self, dataset, params):
        self.start_time = datetime.now()
        self.dataset_id = dataset
        self.params = params
        self.deleted = False # never actually delete information... just set flag to True

    def __repr__(self):
        return '<Search ID: {} // Dataset: {}>'.format(self.id, self.dataset_id)

class MS1File(db.Model):

    ''' Represents one MS1 file.
        Associated with a single Dataset.
    '''

    __tablename__ = 'ms1_file'

    id = db.Column(db.Integer, primary_key=True)
    file_path = db.Column(db.String(500)) # one dataset may have multiple rows in table (one per MS1 file)
    deleted = db.Column(db.Boolean)
    original_filename = db.Column(db.String(150))
    dataset_id = db.Column(db.Integer, db.ForeignKey('dataset.id'))
    created_time = db.Column(db.DateTime)

    def __init__(self, file_path, dataset_id, original_filename=None):
        self.file_path = file_path
        self.dataset_id = dataset_id
        self.created_time = datetime.now()
        self.original_filename = original_filename
        self.deleted = False # never actually delete information... just set flag to True

    def __repr__(self):
        return '<MS1File ID: {} // File Path: {} // Dataset: {}>'.format(self.id, self.file_path, self.dataset_id)

class MS2File(db.Model):

    ''' Represents one MS2 file.
        Associated with a single Dataset.
    '''

    __tablename__ = 'ms2_file'

    id = db.Column(db.Integer, primary_key=True)
    file_path = db.Column(db.String(500)) # one dataset may have multiple rows in table (one per MS2 file)
    deleted = db.Column(db.Boolean)
    scans = db.Column(db.Integer)
    original_filename = db.Column(db.String(150))
    dataset_id = db.Column(db.Integer, db.ForeignKey('dataset.id'))
    created_time = db.Column(db.DateTime)

    def __init__(self, file_path, dataset_id, original_filename=None):
        self.file_path = file_path
        self.dataset_id = dataset_id
        self.created_time = datetime.now()
        self.original_filename = original_filename
        self.deleted = False # never actually delete information... just set flag to True

    def __repr__(self):
        return '<MS2File ID: {} // File Path: {} // Dataset: {}>'.format(self.id, self.file_path, self.dataset_id)

####### BEGIN SEARCH FILES #######

class SQTFile(db.Model):

    ''' Represents one SQT file.
        Associated with a single DBSearch.
    '''

    __tablename__ = 'sqt_file'

    id = db.Column(db.Integer, primary_key=True)
    file_path = db.Column(db.String(500)) # one dataset may have multiple rows in table (one per MS2 file)
    original_filename = db.Column(db.String(150))
    dbsearch_id = db.Column(db.Integer, db.ForeignKey('db_search.id'))
    created_time = db.Column(db.DateTime)
    scans = db.Column(db.Integer)
    deleted = db.Column(db.Boolean)

    def __init__(self, file_path, dbsearch_id, original_filename=None):
        self.file_path = file_path
        self.dbsearch_id = dbsearch_id
        self.created_time = datetime.now()
        self.original_filename = original_filename
        self.deleted = False # never actually delete information... just set flag to True

    def __repr__(self):
        return '<SQTFile ID: {} // File Path: {} // DBSearch ID: {}>'.format(self.id, self.file_path, self.dbsearch_id)

class DTAFile(db.Model):

    ''' Represents one DTASelect-filter.txt file.
        Associated with a single DBSearch.
    '''

    __tablename__ = 'dta_file'

    id = db.Column(db.Integer, primary_key=True)
    file_path = db.Column(db.String(500)) # one dataset may have multiple rows in table (one per MS2 file)
    original_filename = db.Column(db.String(150))
    dbsearch_id = db.Column(db.Integer, db.ForeignKey('db_search.id'))
    created_time = db.Column(db.DateTime)
    deleted = db.Column(db.Boolean)

    # DTASelect flags used for filtering, e.g. '-p 2 -m 0 --trypstat'
    flags = db.Column(db.String(100))

    def __init__(self, file_path, dbsearch_id, original_filename=None):
        self.file_path = file_path
        self.dbsearch_id = dbsearch_id
        self.created_time = datetime.now()
        self.original_filename = original_filename
        self.deleted = False # never actually delete information... just set flag to True

    def __repr__(self):
        return '<DTAFile ID: {} // File Path: {} // DBSearch ID: {}>'.format(self.id, self.file_path, self.dbsearch_id)

####### END SEARCH FILES #######

class CelerySearchTask(db.Model):

    ''' Represents a Celery search subtask (associated with 1 DBSearch)
    '''

    __tablename__ = 'celery_search_task'

    child_task_id = db.Column(db.String(36), primary_key=True) # Celery task ID (subtask)
    group_task_id = db.Column(db.String(36), db.ForeignKey('db_search.celery_id')) # Celery task ID (group)
    status = db.Column(db.String(50)) # status of this task (subtask)
    last_updated = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    def __init__(self, group_task_id, child_task_id, status):
        self.group_task_id = group_task_id
        self.child_task_id = child_task_id
        self.status = status

    def __repr__(self):
        return '<CelerySearchTask Task ID: {}>'.format(self.child_task_id)
