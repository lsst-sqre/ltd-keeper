"""Development mode configurations for ltd-keeper.

These configurations are used by the run.py script.
"""

import os

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, '../ltd-keeper-dev.sqlite')

DEBUG = True
IGNORE_AUTH = True
SECRET_KEY = 'secret-key'
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    'sqlite:///' + db_path
DEFAULT_USER = 'user'
DEFAULT_PASSWORD = 'pass'
