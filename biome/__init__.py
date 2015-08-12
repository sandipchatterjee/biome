#!/usr/bin/env python3

from flask import Flask, Blueprint
from flask_wtf import Form

api = Blueprint('api', __name__)
app = Flask(__name__, static_folder='static')

import biome.views

@app.errorhandler(404)
def not_found(error):
    return '404 error!', 404

app.register_blueprint(api, url_prefix='/api')

