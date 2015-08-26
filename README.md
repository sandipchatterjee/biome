# Biome

_Python-based web application for metaproteomic analysis of microbiome samples_

## Major Requirements

* Python 3.4+
* Flask
* Pandas/NumPy
* PostgreSQL 9.4+ (local or remote)
* see ***requirements.txt*** for details

## Getting Started

* Clone this repo and cd into root (biome) directory
* Create a virtualenv: `$ pyvenv venv`
* Activate virtualenv: `$ source venv/bin/activate`
* Install dependencies: `(venv) $ pip install -r requirements.txt`
* Run (dev) server: `(venv) $ python manage.py runserver`

## Starting Celery Task Queue
*(optional, but needed for some functionality)*

* Launch Redis: `redis-server` (connection details are in **config.py**)
* Launch Celery worker (can launch in the foreground using a second terminal window)
    * Activate venv in new terminal: `$ source venv/bin/activate`
    * Launch worker process: `(venv) $ celery worker -A biome.celery --loglevel=info`