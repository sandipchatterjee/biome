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

class TestSQTFileAPI(base.BaseSQTFileCreatedTestCase):

    ''' Methods to test 'SQTFile' JSON API view functions
    '''

    def test_sqtfile_found_gives_correct_json_output(self):

        ''' Tests that a SQTFile exists (id=1),
            returns a valid JSON object as a response,
            and that this object contains the 'id' key 
            and that response['id']==1
        '''

        try:
            json_resp = json.loads(views_helpers.get_json_response('api.sqtfile_quickinfo', 1))
        except (ValueError, TypeError):
            self.fail('Invalid JSON')

        self.assertIn('id', json_resp)
        self.assertEqual(json_resp['id'], 1)

    def test_sqtfile_not_found_gives_empty_json_obj(self):

        ''' Tests that a SQTFile that doesn't exist (id=2)
            returns an empty JSON object as a response
        '''

        self.assertEqual(views_helpers.get_json_response('api.sqtfile_quickinfo', 2), '{}')

class TestDTAFileAPI(base.BaseDTAFileCreatedTestCase):

    ''' Methods to test 'DTAFile' JSON API view functions
    '''

    def test_dtafile_found_gives_correct_json_output(self):

        ''' Tests that a DTAFile exists (id=1),
            returns a valid JSON object as a response,
            and that this object contains the 'id' key 
            and that response['id']==1
        '''

        try:
            json_resp = json.loads(views_helpers.get_json_response('api.dtafile_quickinfo', 1))
        except (ValueError, TypeError):
            self.fail('Invalid JSON')

        self.assertIn('id', json_resp)
        self.assertEqual(json_resp['id'], 1)

    def test_dtafile_not_found_gives_empty_json_obj(self):

        ''' Tests that a DTAFile that doesn't exist (id=2)
            returns an empty JSON object as a response
        '''

        self.assertEqual(views_helpers.get_json_response('api.dtafile_quickinfo', 2), '{}')

    def test_dtafile_JSON_parser_returns_correct_data(self):

        ''' Tests that DTASelect file --> JSON parser returns valid data (based on mock DTAFile)
        '''

        try:
            json_resp = json.loads(views_helpers.get_json_response('api.dtafile_json', 1))
        except (ValueError, TypeError):
            self.fail('Invalid JSON')

        self.assertIn('data', json_resp) # JSON response has 'data'

        self.assertEqual(len(json_resp['data']), 9) # 9 loci in this "file"
