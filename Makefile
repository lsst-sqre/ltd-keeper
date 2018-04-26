.PHONY: help install test run db-init db-upgrade db-clean redis worker flower docs docs-clean image docker-push travis-docker-deploy version

VERSION=$(shell FLASK_APP=keeper LTD_KEEPER_PROFILE=development flask version)

help:
	@echo "Make command reference"
	@echo "  make install ... (install app for development)"
	@echo "  make test ...... (run unit tests pytest)"
	@echo "  make run ....... (run Flask dev server)"
	@echo "  make db-init ... (create a dev DB with an admin user)"
	@echo "  make db-upgrade  (apply any migrations to the current DB)"
	@echo "  make db-clean .. (delete development sqlite DB)"
	@echo "  make redis ..... (start a Redis Docker container)"
	@echo "  make worker .... (start a Celery worker)"
	@echo "  make flower .... (start the Flower task monitor)"
	@echo "  make docs ...... (make Sphinx docs)"
	@echo "  make docs-clean  (clean Sphinx docs)"
	@echo "  make image ..... (make tagged Docker image)"
	@echo "  make travis-docker-deploy (push image to Docker Hub from Travis CI)"
	@echo "  make version ... (print the app version)"

install:
	pip install -e ".[dev]"

test:
	pytest --flake8 --cov=keeper

run:
	FLASK_APP=keeper LTD_KEEPER_PROFILE=development flask run

db-init:
	FLASK_APP=keeper LTD_KEEPER_PROFILE=development flask createdb
	FLASK_APP=keeper LTD_KEEPER_PROFILE=development flask init

db-upgrade:
	FLASK_APP=keeper LTD_KEEPER_PROFILE=development flask db upgrade

db-clean:
	rm ltd-keeper-dev.sqlite
	rm ltd-keeper-test.sqlite

redis:
	docker run --rm --name redis-dev -p 6379:6379 redis

worker:
	celery worker -A keeper.celery.celery_app -E -l DEBUG

flower:
	celery -A keeper.celery.celery_app flower

docs:
	$(MAKE) -C docs html

docs-clean:
	$(MAKE) -C docs clean

image:
	python setup.py sdist
	docker build --build-arg VERSION=$(VERSION) -t lsstsqre/ltd-keeper:build .

travis-docker-deploy:
	./bin/travis-docker-deploy.sh lsstsqre/ltd-keeper build

version:
	FLASK_APP=keeper LTD_KEEPER_PROFILE=development flask version
