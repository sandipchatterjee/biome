#!/usr/bin/env python3

import os
import logging
from flask import ( Blueprint, 
                    Flask, 
                    render_template, 
                    request, 
                    )
from celery import Celery
from flask.ext.sqlalchemy import SQLAlchemy
from flask_wtf import Form
from biome.config import set_config
from logging.handlers import RotatingFileHandler

api = Blueprint('api', __name__)
data = Blueprint('data', __name__)
search = Blueprint('search', __name__)

app = Flask(__name__, static_folder='static')
logging_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

info_handler = RotatingFileHandler('log_biome_info.log', maxBytes=10000, backupCount=1)
info_handler.setLevel(logging.INFO)
info_handler.setFormatter(logging_formatter)

error_handler = RotatingFileHandler('log_biome_error.log', maxBytes=10000, backupCount=1)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(logging_formatter)

app.logger.addHandler(info_handler)
app.logger.addHandler(error_handler)
set_config(app)

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'], backend=app.config['CELERY_RESULT_BACKEND'])

db = SQLAlchemy(app)

import biome.views
import biome.models

@app.errorhandler(404)
def not_found(error):
    wrong_url = request.path
    return render_template('404.html', wrong_url=wrong_url), 404

app.register_blueprint(api, url_prefix='/api')
app.register_blueprint(data, url_prefix='/data')
app.register_blueprint(search, url_prefix='/search')