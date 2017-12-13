######################################################
Installing and configuring for development and testing
######################################################

Installation
============

LTD Keeper requires Python 3.5.

You can get the application by cloning the Git repository:

.. code-block:: bash

   git clone https://github.com/lsst-sqre/ltd-keeper.git

Install the pre-requisites with :command:`pip`:
Install for development:

.. code-block:: bash

   cd ltd-keeper
   make install

LTD Keeper also uses `SQLite <http://www.sqlite.org>`_ in development and testing modes (any SQL server can be used in production).

Running Tests: pytest
======================

You can invoke the `pytest <http://pytest.org/latest/>`_-based tests by running:

.. code-block:: bash

   make test

Running for development: run.py runserver
=========================================

The 'development' configuration profile provides useful defaults for running an LTD Keeper instance locally (see :file:`config.py`).

Run LTD Keeper in development mode via:

.. code-block:: bash

   ./run.py createdb
   ./run.py init
   ./run.py runserver

The ``createdb`` subcommand creates tables in a development database, and the ``init`` command seeds a default user.
This default user has username ``user`` and password ``pass``.

Once the development DB is prepared you can skip the ``createdb`` and ``init`` commands with later instantiations of ``runserver``.
