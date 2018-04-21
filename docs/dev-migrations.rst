##############################
Developing database migrations
##############################

LTD Keeper uses `Alembic`_ (via `Flask-Migrate`_) to manage SQL database schema migrations.
The entire schema is encoded in Alembic such that Alembic can build a DB schema from scratch.
This page describes how to create a schema migration.
See :doc:`gke-migrations` for applying these migrations to production environments.

Creating a migration
====================

Migrations occur whenever the DB schema changes.
This includes adding, renaming or removing a column.
This also includes changing indices or constraints on columns.

In the same Git commit as the DB model is being changed, create the migration:

.. code-block:: bash

   FLASK_APP=keeper flask db migrate -m "message"

Use the *message* to briefly describes the schema change.
This command will auto-generate a migration script in :file:`migrations/versions`.
Review that script and commit it.

Testing a migration
===================

The migration can be tested locally if you have a development DB running a previous version of the schema:

.. code-block:: bash

   make db-upgrade
   make run

With a :doc:`staging deployment <gke-staging-deployment-playbook>`, it is also possible to :doc:`test migrations <gke-migrations>` against a copy of the production database.
This is now recommended practice.

Coding for migrations
=====================

By default, migrations only update the schema of a DB, not the data within it.
It is up to the developer to package data updates that go along with the migration.
There are two ways to do this:

1. Write an update script that can be run after the schema migration that populates any new columns or tables.
   Ideally, this code can be part of the Alembic migration itself using the `sqlalchemy.execute` API.
   See the blog post `Alembic: Data Migrations`_ for an example.

2. Write the application code such that it dynamically updates and populates the database.

.. _Alembic: https://alembic.readthedocs.io/
.. _Flask-Migrate: https://flask-migrate.readthedocs.io/
.. _`Alembic: Data Migrations`: http://www.georgevreilly.com/blog/2016/09/06/AlembicDataMigrations.html
