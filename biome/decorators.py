#!/usr/bin/env python3

from threading import Thread

def async(f):

    ''' Decorator for running f() in a separate thread
        (from http://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-xi-email-support )
        
        Will change to processes/multiprocessing pool to avoid GIL if necessary...
    '''

    def wrapper(*args, **kwargs):
        thr = Thread(target=f, args=args, kwargs=kwargs)
        thr.start()

    return wrapper