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

Running for development
=======================

The 'development' configuration profile provides useful defaults for running an LTD Keeper instance locally (see :file:`config.py`).

Run LTD Keeper in development mode via:

Running LTD Keeper locally requires three separate terminal sessions.

In the first:

.. code-block:: bash

   make redis

In the second:

.. code-block:: bash

   make db-init
   make run

In the third:

.. code-block:: bash

   make worker

The ``make db-init`` command creates tables in a development database with a default user.
This default user has username ``user`` and password ``pass``.

Using httpie, you can get an auth token by running:

.. code-block:: bash

   http --auth user:pass get :5000/token

Once the development DB is prepared you can skip the ``make db-init`` commands.

Clean up the development DB by running:

.. code-block:: bash

   make db-clean
