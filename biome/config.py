import os

class BaseConfig(object):

    ''' Base configuration class for Biome app
    '''

    DEBUG = False
    TESTING = False

    SECRET_KEY = 'secret_key_from_env'
    UPLOAD_FOLDER = os.getcwd()+'/'+'biome/data_files'
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
    CELERY_ROUTES = {   'biome_worker.echo' : {'queue': 'sandip'},
                        'biome_worker.sum' : {'queue': 'sandip'},
                        'biome_worker.tsum' : {'queue': 'sandip'},
                        }

    CELERY_TASK_SERIALIZER = 'pickle'
    CELERY_RESULT_SERIALIZER = 'pickle'

    SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://'

class ProdConfig(BaseConfig):

    ''' Production configuration class (TSRI)
    '''

    # Connect String: postgresql+psycopg2://user:password@host:port/dbname[?key=value&key=value...]
    # local postgres install on web server
    SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://biome@localhost:5432/biome'
    CELERY_BROKER_URL = 'redis://wl-cmadmin:6379/0'
    CELERY_RESULT_BACKEND = 'redis://wl-cmadmin:6379'

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

    # might change this to SQLite in the future... (doesn't have JSON support)
    SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://sandip@localhost:5432/biometesting'
    # SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

config = {  'development': 'biome.config.DevConfig', 
            'testing': 'biome.config.TestConfig', 
            'development_tsri': 'biome.config.DevConfigTSRI', 
            'production_tsri': 'biome.config.ProdConfig', 
            'default': 'biome.config.DevConfig', 
            }

def set_config(app):

    ''' Sets configuration for app using $BIOME_CONFIG environment variable
        ($BIOME_CONFIG should be set to 'default')
    '''

    config_name = os.getenv('BIOME_CONFIG', 'default')
    app.config.from_object(config[config_name])

    logger_info = 'Using app configuration {} ({}) -- Set environment variable $BIOME_CONFIG to one of ({}) to change'
    app.logger.info(logger_info.format( config_name, 
                                        config[config_name], 
                                        ','.join(config.keys())
                                        ))
