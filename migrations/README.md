# Migrations

This directory contains DB migrations managed by [Alembic](https://alembic.readthedocs.io) through [Flask-Migrate](https://flask-migrate.readthedocs.io).

## Making a migration

```
./run.py db migrate -m "migration message"
```

Review and edit the migration strategy as necessary.
These migrations must be checked into the Git repository to tie the DB schema to Git versioning.

## Running a migration

```
./run.py db upgrade
```

This will upgrade the DB to the state specified in the app's Git repository.

* * * *

This directory was originally created with 

```
./run.py db init
```
