"""Testing mode configurations for ltd-keeper.

These configurations are used when running any tests.
"""

import os

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, '../ltd-keeper-test.sqlite')

DEBUG = False
TESTING = True
IGNORE_AUTH = False
SECRET_KEY = 'secret-key'
SERVER_NAME = 'testing.io'
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    'sqlite:///' + db_path
