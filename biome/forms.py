#!/usr/bin/env python3

from flask.ext.wtf import Form
from wtforms import (   BooleanField, 
                        DecimalField, 
                        HiddenField, 
                        IntegerField, 
                        RadioField, 
                        SelectField, 
                        StringField, 
                        SubmitField, 
                        TextAreaField, 
                        validators, 
                    )
from flask_wtf.file import FileField, FileRequired

class DatasetUploadForm(Form):

    ''' DatasetUploadForm is a WTForm Form object for uploading data files
    '''

    dataset_name = StringField('Dataset name:', [validators.Required(), validators.length(max=60)])
    data_file = FileField('Data file:', [validators.Required()])
    dataset_desc = TextAreaField('Description:', [validators.optional(), validators.length(max=500)])
    submit = SubmitField('Upload Data')

class SearchParamsForm(Form):

    ''' SearchParamsForm is a WTForm Form object for proteomic search parameters
    '''

    search_name = StringField(  'Search name',
                                [validators.Required(), validators.length(max=60)], 
                                )

    diff_search_options = StringField(  'Differential Search Options (diffmods)', 
                                        default='15.9949 M', 
                                        )
    diff_search_Nterm = StringField(    'N-terminal diffmod',
                                        default=None,
                                        )
    diff_search_Cterm = StringField(    'C-terminal diffmod',
                                        default=None,
                                        )
    default_mongodb_uri = ','.join(('node0097:27018', 
                                    'node0129:27018', 
                                    'node0401:27018', 
                                    'node0441:27018', 
                                    'node0481:27018', 
                                    'node0521:27018', 
                                    'node0561:27018', 
                                    'node0601:27018', 
                                    'node0617:27018', 
                                    'node0649:27018', 
                                    'node0953:27018', 
                                    'node0985:27018', 
                                    'node1001:27018', 
                                    'nodea1331:27018', 
                                    'nodea1431:27018', 
                                    'node0113:27018', 
                                    'node0145:27018', 
                                    'node0411:27018', 
                                    'node0421:27018', 
                                    'node0431:27018', 
                                    'node0451:27018', 
                                    'node0461:27018', 
                                    'node0471:27018', 
                                    'node0491:27018', 
                                    'node0501:27018', 
                                    'node0511:27018', 
                                    'node0531:27018', 
                                    'node0541:27018', 
                                    'node0551:27018', 
                                    'node0571:27018', 
                                    'node0581:27018', 
                                    'node0591:27018', 
                                    'node0633:27018', 
                                    'node0665:27018', 
                                    'node0681:27018', 
                                    'node0921:27018', 
                                    'node0937:27018', 
                                    'node0969:27018', 
                                    'nodea1301:27018', 
                                    'nodea1401:27018', 
                                    ))
    mongodb_uri = StringField( 'MongoDB URI', 
                                default='mongodb://'+default_mongodb_uri, 
                                )
    is_sharded = BooleanField(  'Database is sharded',
                                default=True, 
                                )
    massdb_name = StringField(  'MassDB database',
                                default='MassDB_072114', 
                                )
    massdbcoll = StringField(   'MassDB collection',
                                default='MassDB_072114', 
                                )
    use_seqdb = BooleanField(   'Use SeqDB to lookup parent proteins for identified peptides', 
                                default=True, 
                                )
    seqdb_name = StringField(   'SeqDB database name',
                                default='SeqDB_072114', 
                                )
    seqdbcoll = StringField(    'SeqDB collection',
                                default='SeqDB_072114', 
                                )
    use_protdb = BooleanField(  'Use ProtDB to lookup Protein ID values', 
                                default=False, 
                                )
    protdb_name = StringField(  'ProtDB database name',
                                default='ProtDB_072114', 
                                )
    protdbcoll = StringField(   'ProtDB collection',
                                default='ProtDB_072114', 
                                )
    blazmass_jar = StringField( 'Path to Blazmass JAR', 
                                default='/gpfs/home/gstupp/blazmass/blazmass.jar', 
                                )
    dtaselect_classpath = StringField(   'Path to DTASelect (classpath)', 
                                    default='/gpfs/home/gstupp/DTASelect2', 
                                    )
    temp = StringField(        'Temporary directory name', 
                                default='dummy', 
                                )
    verbose = BooleanField(    'Verbose logging', 
                                default=True, 
                                )
    ppm_peptide_mass_tolerance = DecimalField(  'ppm precursor (peptide) mass tolerance',
                                                places=1, 
                                                default=30.0
                                                )
    ppm_fragment_ion_tolerance = DecimalField(  'ppm fragment ion tolerance', 
                                                places=1, 
                                                default=50.0, 
                                                )
    ppm_fragment_ion_tolerance_high = BooleanField( 'ppm fragment ion tolerance/high',
                                                    default=False, 
                                                    )

    server_preset = StringField(    'Computing cluster',
                                    default='garibaldi', 
                                    )
    numcores = IntegerField(    '# cores per job',
                                    default=4, 
                                    )
    numthreads = IntegerField(  '# search threads per job',
                                    default=4, 
                                    )
    walltime = IntegerField(    '# hours walltime per job',
                                    default=8, 
                                    )
    split_n = IntegerField(     '# files to split each MS2 file into',
                                    default=10, 
                                    )

    sfp = DecimalField( 'Peptide False Discovery Rate',
                        places=2,
                        default=0.01, 
                        )
    ppp = IntegerField( '# required peptides per protein',
                        default=2, 
                        )
    use_job_spacing = BooleanField(    'Use job submission spacing', 
                                )
    job_spacing = IntegerField( '# minutes to wait between submitting jobs',
                                default=1, 
                                )
    job_spacing_init = IntegerField(    '# jobs to submit initially (if using job_spacing)',
                                        default=0, 
                                        )
    submit = SubmitField('Run Search')
