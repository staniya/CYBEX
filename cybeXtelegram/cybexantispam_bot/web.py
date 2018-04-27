from bottle import Bottle, run
from web_util import setup_web_app

'''
Bottle is a fast, simple and 
lightweight WSGI micro web-framework for Python. 
It is distributed as a single file module and 
has no dependencies other than the Python Standard Library.
'''

app = Bottle()
setup_web_app(app)

if __name__ == '__main__':
    run(app, host='localhost', port=8888)