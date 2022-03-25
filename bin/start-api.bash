#!/bin/bash

set -eu

flask createdb migrations/alembic.ini
flask init
uwsgi uwsgi.ini
