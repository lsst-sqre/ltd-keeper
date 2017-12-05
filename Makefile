.PHONY: help install test docs docs-clean image docker-push travis-docker-deploy

VERSION=$(shell python run.py version)

help:
	@echo "Make command reference"
	@echo "  make install ... (install app for development)"
	@echo "  make test ...... (run unit tests pytest)"
	@echo "  make docs ...... (make Sphinx docs)"
	@echo "  make docs-clean  (clean Sphinx docs)"
	@echo "  make image ..... (make tagged Docker image)"
	@echo "  make travis-docker-deploy (push image to Docker Hub from Travis CI)"

install:
	pip install -e ".[dev]"

test:
	pytest --flake8 --cov=keeper

docs:
	$(MAKE) -C docs html

docs-clean:
	$(MAKE) -C docs clean

image:
	python setup.py sdist
	docker build --build-arg VERSION=$(VERSION) -t lsstsqre/ltd-keeper:build .

travis-docker-deploy:
	./bin/travis-docker-deploy.sh lsstsqre/ltd-keeper build
