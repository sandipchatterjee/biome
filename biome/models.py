#!/usr/bin/env python3

from biome import ( app, db,
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

    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.uploaded_time = datetime.now()

    def __repr__(self):
        return '<Dataset ID: {}>' % self.username

class DBSearch(db.Model):

    ''' Represents a Blazmass/ComPIL Search.
        Associated with a single Dataset.
    '''

    __tablename__ = 'db_search'

    id = db.Column(db.Integer, primary_key=True)
    params = db.Column(postgresql.JSON)
    start_time = db.Column(db.DateTime)

    dataset_id = db.Column(db.Integer, db.ForeignKey('dataset.id'))
    dataset = db.relationship('Dataset', backref=db.backref('ms2file', lazy='dynamic'))

    def __init__(self):
        self.start_time = datetime.now()
        self.dataset_id = dataset

    def __repr__(self):
        return '<Search ID: {}>'.format(self.id)

class MS2File(db.Model):

    ''' Represents one MS2 file.
        Associated with a single Dataset.
    '''

    __tablename__ = 'ms2_file'

    id = db.Column(db.Integer, primary_key=True)
    file_path = db.Column(db.String(500)) # one dataset may have multiple rows in table (one per MS2 file)

    dataset_id = db.Column(db.Integer, db.ForeignKey('dataset.id'))
    dataset = db.relationship('Dataset', backref=db.backref('ms2file', lazy='dynamic'))
    created_time = db.Column(db.DateTime)

    def __init__(self, file_path, dataset_id):
        self.file_path = file_path
        self.dataset_id = dataset
        self.created_time = datetime.now()

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
    dbsearch_id = db.Column(db.Integer, db.ForeignKey('db_search.id'))
    dbsearch = db.relationship('db_search', backref=db.backref('sqtfile', lazy='dynamic'))
    created_time = db.Column(db.DateTime)

    def __init__(self, file_path, dbsearch_id):
        self.file_path = file_path
        self.dbsearch_id = dbsearch_id
        self.created_time = datetime.now()

    def __repr__(self):
        return '<SQTFile ID: {} // File Path: {} // DBSearch ID: {}>'.format(self.id, self.file_path, self.dbsearch_id)

class DTAFile(db.Model):

    ''' Represents one DTASelect-filter.txt file.
        Associated with a single DBSearch.
    '''

    __tablename__ = 'dta_file'

    id = db.Column(db.Integer, primary_key=True)
    file_path = db.Column(db.String(500)) # one dataset may have multiple rows in table (one per MS2 file)
    dbsearch_id = db.Column(db.Integer, db.ForeignKey('db_search.id'))
    dbsearch = db.relationship('db_search', backref=db.backref('dtafile', lazy='dynamic'))
    created_time = db.Column(db.DateTime)

    # DTASelect flags used for filtering, e.g. '-p 2 -m 0 --trypstat'
    flags = db.Column(db.String(100))

    def __init__(self, file_path, dbsearch_id):
        self.file_path = file_path
        self.dbsearch_id = dbsearch_id
        self.created_time = datetime.now()

    def __repr__(self):
        return '<DTAFile ID: {} // File Path: {} // DBSearch ID: {}>'.format(self.id, self.file_path, self.dbsearch_id)

####### END SEARCH FILES #######