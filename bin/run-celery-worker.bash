#!/bin/bash

echo $PATH
which celery
celery worker -A keeper.celery.celery_app -E -l INFO
