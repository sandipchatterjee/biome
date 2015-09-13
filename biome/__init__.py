#!/usr/bin/env python3

import os
from flask import ( Blueprint, 
                    Flask, 
                    render_template, 
                    request, 
                    )
from celery import Celery
from flask.ext.sqlalchemy import SQLAlchemy
from flask_wtf import Form
from biome.config import set_config

api = Blueprint('api', __name__)
data = Blueprint('data', __name__)
search = Blueprint('search', __name__)

app = Flask(__name__, static_folder='static')
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