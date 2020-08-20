VERSION=$(shell FLASK_APP=keeper LTD_KEEPER_PROFILE=development flask version)

help:
	@echo "Make command reference"
	@echo "  make update-deps (update pinned dependencies)"
	@echo "  make init ...... (install for development)"
	@echo "  make update .....(update dependencies and reinstall)"
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

.PHONY: update-deps
update-deps:
	pip install --upgrade pip-tools pip setuptools
	pip-compile --upgrade --build-isolation --generate-hashes --output-file requirements/main.txt requirements/main.in
	pip-compile --upgrade --build-isolation --generate-hashes --output-file requirements/dev.txt requirements/dev.in

.PHONY: init
init:
	pip install --editable .
	pip install --upgrade -r requirements/main.txt -r requirements/dev.txt

.PHONY: update
update: update-deps init

.PHONY: test
test:
	pytest --flake8 --cov=keeper

.PHONY: run
run:
	FLASK_APP=keeper LTD_KEEPER_PROFILE=development flask run

.PHONY: db-init
db-init:
	FLASK_APP=keeper LTD_KEEPER_PROFILE=development flask createdb
	FLASK_APP=keeper LTD_KEEPER_PROFILE=development flask init

.PHONY: db-upgrade
db-upgrade:
	FLASK_APP=keeper LTD_KEEPER_PROFILE=development flask db upgrade

.PHONY: db-clean
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
