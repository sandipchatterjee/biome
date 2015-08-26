import os

class BaseConfig(object):

    ''' Base configuration class for Biome app
    '''

    DEBUG = False
    TESTING = False

    SECRET_KEY = 'secret_key_from_env'
    UPLOAD_FOLDER = os.getcwd()+'/'+'biome/data_files'

    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

    SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://'

class DevConfig(BaseConfig):

    ''' Dev server configuration class
    '''

    DEBUG = True
    TESTING = True

    # Connect String: postgresql+psycopg2://user:password@host:port/dbname[?key=value&key=value...]
    # local development postgres install:
    SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://sandip@localhost:5432/biome'

class DevConfigTSRI(DevConfig):

    ''' Dev server config, but when on-campus at TSRI
        (uses Redis host on local network)
    '''

    CELERY_BROKER_URL = 'redis://wl-cmadmin:6379/0'
    CELERY_RESULT_BACKEND = 'redis://wl-cmadmin:6379'

class TestConfig(BaseConfig):

    ''' Testing-only configuration class
    '''

    DEBUG = False
    TESTING = True

config = {  'development': 'biome.config.DevConfig', 
            'testing': 'biome.config.TestConfig', 
            'development_tsri': 'biome.config.DevConfigTSRI', 
            'default': 'biome.config.DevConfig', 
            }

def set_config(app):

    ''' Sets configuration for app using $BIOME_CONFIG environment variable
        ($BIOME_CONFIG should be set to 'default')
    '''

    config_name = os.getenv('BIOME_CONFIG', 'default')
    app.config.from_object(config[config_name])

    app.logger.info('Using app configuration {} ({}) -- Set environment variable $BIOME_CONFIG to change'.format(config_name, config[config_name]))
