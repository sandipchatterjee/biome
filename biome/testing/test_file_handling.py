#!/usr/bin/env python3

import io
import os
import time
from werkzeug.datastructures import FileStorage
from werkzeug import secure_filename
from tempfile import mkstemp

from biome import ( app, 
                    db, 
                    models, 
                    views, 
                    views_documents, 
                    views_helpers, 
                    )
from biome.testing import base

class TestSaveFile(base.BaseFileInfoTestCase):

    ''' Methods to test saving files to uploads directory
    '''

    def setUp(self):
        super().setUp()
        self.ms1_tmp_file_path = mkstemp()[1]
        self.ms2_tmp_file_path = mkstemp()[1]
        self.sqt_tmp_file_path = mkstemp()[1]
        self.dta_tmp_file_path = mkstemp()[1]

        self.ms1_filehandle = open(self.ms1_tmp_file_path)
        self.ms2_filehandle = open(self.ms2_tmp_file_path)
        self.sqt_filehandle = open(self.sqt_tmp_file_path)
        self.dta_filehandle = open(self.dta_tmp_file_path)

        self.ms1_filestorage = FileStorage(stream=self.ms1_filehandle, filename=self.ms1_file_name)
        self.ms2_filestorage = FileStorage(stream=self.ms2_filehandle, filename=self.ms2_file_name)
        self.sqt_filestorage = FileStorage(stream=self.sqt_filehandle, filename=self.sqt_file_name)
        self.dta_filestorage = FileStorage(stream=self.dta_filehandle, filename=self.dta_file_name)

        self.new_ms1_file_path, self.new_ms2_file_path, self.new_sqt_file_path, self.new_dta_file_path = (None,)*4

    def tearDown(self):
        try:
            for new_file_path in (  self.new_ms1_file_path, 
                                    self.new_ms2_file_path, 
                                    self.new_sqt_file_path, 
                                    self.new_dta_file_path, 
                                    self.ms1_tmp_file_path, 
                                    self.ms2_tmp_file_path, 
                                    self.sqt_tmp_file_path, 
                                    self.dta_tmp_file_path, 
                                    ):
                if new_file_path:
                    os.remove(new_file_path)
        finally:
            for filehandle in ( self.ms1_filehandle, 
                                self.ms2_filehandle, 
                                self.sqt_filehandle, 
                                self.dta_filehandle, 
                                ):
                filehandle.close()

        super().tearDown()

    def test_save_new_ms1_file(self):

        ''' tests saving new MS1 file using save_new_file
        '''

        self.new_ms1_file_path, _ = views_documents.save_new_file(self.ms1_filestorage)
        # (not saving 'original_filename' returned from save_new_file)

        self.assertTrue(os.path.exists(self.new_ms1_file_path))

    def test_save_new_ms2_file(self):

        ''' tests saving new MS2 file using save_new_file
        '''

        self.new_ms2_file_path, _ = views_documents.save_new_file(self.ms2_filestorage)
        # (not saving 'original_filename' returned from save_new_file)

        self.assertTrue(os.path.exists(self.new_ms2_file_path))

    def test_save_new_sqt_file(self):

        ''' tests saving new SQT file using save_new_file
        '''

        self.new_sqt_file_path, _ = views_documents.save_new_file(self.sqt_filestorage)
        # (not saving 'original_filename' returned from save_new_file)

        self.assertTrue(os.path.exists(self.new_sqt_file_path))

    def test_save_new_dta_file(self):

        ''' tests saving new DTASelect-filter file using save_new_file
        '''

        self.new_dta_file_path, _ = views_documents.save_new_file(self.dta_filestorage)
        # (not saving 'original_filename' returned from save_new_file)

        self.assertTrue(os.path.exists(self.new_dta_file_path))

    def test_original_filename_is_preserved(self):

        ''' test that werkzeug FileStorage.filename is the same as the input
            'original_filename' 
        '''

        _, self.original_filename = views_documents.save_new_file(self.ms1_filestorage)

        self.assertTrue(self.original_filename == secure_filename(self.ms1_filestorage.filename))

class FileValidationTests(base.BaseFileSavedTestCase):

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_list_of_valid_filenames(self):

        ''' tests user trying to upload a valid collection of files
        '''

        file_list = (   '121614_SC_sampleH1sol_25ug_pepstd_HCD_FTMS_MS2_07_11.ms2', 
                        '082815_H1_velos1_FTMS_MS2_hcd35_06.ms1', 
                        '121614_SC_sampleH1sol_25ug_pepstd_HCD_FTMS_MS2_07_11.sqt', 
                        'DTASelect-filter.txt', 
                        '121614_SC_sampleH1sol_DTASelect-filter.txt', 
                        )

        self.assertTrue(views_documents.check_file_types(file_list))

    def test_list_of_invalid_filenames(self):

        ''' tests user trying to upload an invalid collection of files
        '''

        file_list = (   '121614_SC_sampleH1sol_25ug_pepstd_HCD_FTMS_MS2_07_11.ms2', 
                        '082815_H1_velos1_FTMS_MS2_hcd35_06.ms1', 
                        '121614_SC_sampleH1sol_25ug_pepstd_HCD_FTMS_MS2_07_11.sqt', 
                        'DTASelect-filter.txt', 
                        '121614_SC_sampleH1sol_DTASelect-filter.txt', 
                        'some_other_document.pdf', 
                        )

        self.assertFalse(views_documents.check_file_types(file_list))