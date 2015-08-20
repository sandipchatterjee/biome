#!/usr/bin/env python3

from biome import app, db
from flask.ext.script import Server, Manager
from flask.ext.migrate import Migrate, MigrateCommand

if __name__ == '__main__':

    migrate = Migrate(app, db)

    manager = Manager(app)

    server = Server(host='0.0.0.0', port=7777, use_debugger=True, use_reloader=True)
    manager.add_command('runserver', server)
    manager.add_command('db', MigrateCommand)

    manager.run()
