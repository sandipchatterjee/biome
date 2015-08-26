import os

class BaseConfig(object):

    ''' Base configuration class for Biome app
    '''

    DEBUG = False
    TESTING = False

    SECRET_KEY = 'secret_key_from_env'
    UPLOAD_FOLDER = os.getcwd()+'/'+'biome/data_files'

    SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://'

class DevConfig(BaseConfig):

    ''' Dev server configuration class
    '''

    DEBUG = True
    TESTING = True

    # Connect String: postgresql+psycopg2://user:password@host:port/dbname[?key=value&key=value...]
    # local development postgres install:
    SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://sandip@localhost:5432/biome'

class TestConfig(BaseConfig):

    ''' Testing-only configuration class
    '''

    DEBUG = False
    TESTING = True

config = {  'development': 'biome.config.DevConfig', 
            'testing': 'biome.config.TestConfig', 
            'default': 'biome.config.DevConfig', 
            }

def set_config(app):

    ''' Sets configuration for app using $BIOME_CONFIG environment variable
        ($BIOME_CONFIG should be set to 'default')
    '''

    config_name = os.getenv('BIOME_CONFIG', 'default')
    app.config.from_object(config[config_name])