#!/bin/bash

set -eu

echo $PATH
pwd
ls migrations

flask createdb migrations/alembic.ini
flask init
uwsgi uwsgi.ini
