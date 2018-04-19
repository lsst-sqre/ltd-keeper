.PHONY: help install test run db-init db-upgrade docs docs-clean image docker-push travis-docker-deploy version

VERSION=$(shell FLASK_APP=keeper LTD_KEEPER_PROFILE=development flask version)

help:
	@echo "Make command reference"
	@echo "  make install ... (install app for development)"
	@echo "  make test ...... (run unit tests pytest)"
	@echo "  make run ....... (run Flask dev server)"
	@echo "  make db-init ... (create a dev DB with an admin user)"
	@echo "  make db-upgrade  (apply any migrations to the current DB)"
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
