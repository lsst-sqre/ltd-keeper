##################################################
Installing and Configuring for Development/Testing
##################################################

Installation
============

LTD Keeper requires Python 3.5.

You can get the application by cloning the Git repository:

.. code-block:: bash

   git clone https://github.com/lsst-sqre/ltd-keeper.git

Install the pre-requisites with :command:`pip`:

.. code-block:: bash

   cd ltd-keeper
   pip install -r requirements.txt

LTD Keeper also uses `SQLite <http://www.sqlite.org>`_.


Running Tests: py.test
======================

You can invoke the `pytest <http://pytest.org/latest/>`_-based tests by running:

.. code-block:: bash

   py.test

Running for Development: run.py runserver
=========================================

The 'development' configuration profile provides useful defaults for running an LTD Keeper instance locally (see :file:`config.py`).

Run LTD Keeper in development mode via:

.. code-block:: bash

   ./run.py runserver

In development mode a database is automatically initialized.
The default user has username ``user`` and password ``pass``.

..
  Running in Production
  =====================
  
  TODO

..
  Configuration
  =============
  
  Amazon Web Services
  -------------------
  
  LTD Keeper uses Amazon Web Services (AWS) for object storage (S3) and DNS configuration (Route 53).
  `boto3 <http://boto3.readthedocs.org/en/latest/>`_.
  
  Credentials for your AWS account should be stored in a :file:`~/.aws/credentials` file.
  See http://boto3.readthedocs.org/en/latest/guide/quickstart.html#configuration for more information about configuring Boto3.
