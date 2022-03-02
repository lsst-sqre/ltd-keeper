#!/bin/bash

set -eu

echo $PATH

flask createdb migrations/alembic.ini
flask init
uwsgi uwsgi.ini
