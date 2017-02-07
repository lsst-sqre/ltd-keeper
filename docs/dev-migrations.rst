##############################
Developing Database Migrations
##############################

LTD Keeper uses `Alembic`_ (via `Flask-Migrate`_) to manage SQL database schema migrations.
The entire schema is encoded in Alembic such that Alembic can build a DB schema from scratch.
This page describes how to create a schema migration.
See :doc:`gke-migrations` for applying these migrations to production environments.

Creating a Migration
====================

Migrations occur whenever the DB schema changes.
This includes adding, renaming or removing a column.
This also includes changing indices or constraints on columns.

In the same Git commit as the DB model is being changed, create the migration:

.. code-block:: bash

   ./run.py db migrate -m "message"

where the *message* briefly describes the schema change.
This command will auto-generate a migration script in :file:`migrations/versions`.
Review that script

Testing a Migration
===================

The migration can be tested locally if you have a development DB running a previous version of the schema:

.. code-block:: bash

   ./run.py db upgrade
   ./run.py runserver

With a :doc:`staging deployment <gke-staging-deployment-playbook>`, it is also possible to :doc:`test migrations <gke-migrations>` against a copy of the production database.
This is now recommended practice.

Coding for Migrations
=====================

Migrations only update the schema of a DB, not the data within it.
It is up to the developer to package data updates that go along with the migration.
There are two ways to do this:

1. Write an update script that can be run after the migration (or even between a sequence or migrations) that populates any new columns or tables.

2. Write the application code such that it dynamically updates and populates the database.

.. _Alembic: https://alembic.readthedocs.io/
.. _Flask-Migrate: https://flask-migrate.readthedocs.io/
