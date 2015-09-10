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
from flask import ( jsonify, 
                    )
import json

class TestDatasetAPI(base.BaseDatasetCreatedTestCase):

    ''' Methods to test 'Dataset' JSON API view functions
    '''

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_dataset_found_gives_correct_json_output(self):

        ''' Tests that a dataset that exists (id=1)
            returns a valid JSON object as a response,
            and that this object contains the 'id' key 
            and that response['id']==1
        '''

        try:
            json_resp = json.loads(views_helpers.get_json_response('api.dataset_quickinfo', 1))
        except (ValueError, TypeError):
            self.fail('Invalid JSON')

        self.assertIn('id', json_resp)
        self.assertEqual(json_resp['id'], 1)

    def test_dataset_not_found_gives_empty_json_obj(self):

        ''' Tests that a dataset that doesn't exist (id=2)
            returns an empty JSON object as a response
        '''

        self.assertEqual(views_helpers.get_json_response('api.dataset_quickinfo', 2), '{}')

class TestDTAFileParsers(base.BaseDTAFileCreatedTestCase):

    ''' Methods to test DTAFile parsers -- JSON and pandas/CSV
    '''

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()