#!/bin/bash

echo $PATH
which celery
celery -A keeper.celery.celery_app worker -E -l INFO
