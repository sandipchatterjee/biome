#!/usr/bin/env python3

import os
from flask import Flask, Blueprint, render_template, request
from flask.ext.sqlalchemy import SQLAlchemy
from flask_wtf import Form

api = Blueprint('api', __name__)
data = Blueprint('data', __name__)
app = Flask(__name__, static_folder='static')
db = SQLAlchemy(app)

import biome.views
import biome.models

@app.errorhandler(404)
def not_found(error):
    wrong_url = request.path
    return render_template('404.html', wrong_url=wrong_url), 404

app.register_blueprint(api, url_prefix='/api')
app.register_blueprint(data, url_prefix='/data')

app.config['SECRET_KEY'] = 'secret_key_from_env'
UPLOAD_FOLDER = 'biome/data_files'
app.config['UPLOAD_FOLDER'] = os.getcwd()+'/'+UPLOAD_FOLDER

# Connect String: postgresql+psycopg2://user:password@host:port/dbname[?key=value&key=value...]
# local development postgres install:
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://sandip@localhost:5432/biome'


