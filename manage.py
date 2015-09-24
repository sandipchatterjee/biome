#!/usr/bin/env python3

from biome import app, db
from flask.ext.script import Server, Manager
from flask.ext.migrate import Migrate, MigrateCommand
import logging
from logging.handlers import RotatingFileHandler

if __name__ == '__main__':

    logging_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    info_handler = RotatingFileHandler('log_biome_info.log', maxBytes=10000, backupCount=1)
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(logging_formatter)

    error_handler = RotatingFileHandler('log_biome_error.log', maxBytes=10000, backupCount=1)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging_formatter)

    app.logger.addHandler(info_handler)
    app.logger.addHandler(error_handler)

    migrate = Migrate(app, db)

    manager = Manager(app)

    server = Server(host='0.0.0.0', port=7777, use_debugger=True, use_reloader=True)
    manager.add_command('runserver', server)
    manager.add_command('db', MigrateCommand)

    manager.run()
