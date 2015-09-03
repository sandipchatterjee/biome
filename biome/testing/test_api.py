#!/usr/bin/env python3

from biome import ( api, 
                    app, 
                    db, 
                    models, 
                    views, 
                    views_documents, 
                    views_helpers, 
                    )
from biome.testing import base

class TestQuickInfoResponses(base.BaseCompleteDatasetTestCase):

    ''' Methods to test JSON 'quickinfo' API view functions
    '''

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

class TestDTAFileParsers(base.BaseDTAFileCreatedTestCase):

    ''' Methods to test DTAFile parsers -- JSON and pandas/CSV
    '''

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()