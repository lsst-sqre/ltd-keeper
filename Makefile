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
	rm -rf .tox
	pip install --upgrade pre-commit tox
	pip install --pre --upgrade tox-docker
	pre-commit install

.PHONY: update
update: update-deps init

.PHONY: test
test:
	pytest --flake8 --cov=keeper

.PHONY: run
run:
	FLASK_APP=keeper LTD_KEEPER_PROFILE=development LTD_KEEPER_DEV_DB_URL="mysql+pymysql://user:password@localhost:3306/db" flask run

.PHONY: db-init
db-init:
	FLASK_APP=keeper LTD_KEEPER_PROFILE=development LTD_KEEPER_DEV_DB_URL="mysql+pymysql://user:password@localhost:3306/db" flask createdb
	FLASK_APP=keeper LTD_KEEPER_PROFILE=development LTD_KEEPER_DEV_DB_URL="mysql+pymysql://user:password@localhost:3306/db" flask init

.PHONY: db-upgrade
db-upgrade:
	FLASK_APP=keeper LTD_KEEPER_PROFILE=development LTD_KEEPER_DEV_DB_URL="mysql+pymysql://user:password@localhost:3306/db" flask db upgrade

.PHONY: db-clean
db-clean:
	rm -f ltd-keeper-dev.sqlite
	rm -f ltd-keeper-test.sqlite
	rm -rf mysqldb

.PHONY: redis
redis:
	docker run --rm --name redis-dev -p 6379:6379 redis

.PHONY: worker
worker:
	celery -A keeper.celery.celery_app worker -E -l DEBUG

.PHONY: flower
flower:
	celery -A keeper.celery.celery_app flower

.PHONY: docs
docs:
	$(MAKE) -C docs html

.PHONY: docs-clean
docs-clean:
	$(MAKE) -C docs clean

.PHONY: image
image:
	docker build -t lsstsqre/ltd-keeper:build .

.PHONY: version
version:
	FLASK_APP=keeper LTD_KEEPER_PROFILE=development flask version
