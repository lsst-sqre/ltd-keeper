#!/bin/bash

set -eu

echo $PATH

flask createdb
flask init
uwsgi uwsgi.ini
