########################################################
Applying Database Migrations in Production on Kubernetes
########################################################

Unlike regular application code changes, database schema migrations in production require actual downtime.
We haven't built infrastructure to seamlessly switch between schemas in production.

Prerequisites
=============

- This procedure should only be followed for application updates that change DB schema and have an Alembic migration.
  See :doc:`dev-migrations` for information about creating migrations with Alembic.
- A new docker image with the DB change should be pushed to Docker Hub.
- Check if additional steps are needed to apply the migration, such as seeding new data into the DB.

Procedure
=========

1. Bring the deployment down:

   .. code-block:: bash

      kubectl delete deployment keeper-deployment

   Watch for the pods to be deleted with ``kubectl get pods``.

2. Deploy the maintenance pod.

   First update :file:`keeper-mgmt-pod.yaml` with the new uWSGI container's ``image`` name.
   Look for the lines:

   .. code-block:: yaml

      - name: uwsgi
        image: "lsstsqre/ltd-keeper:latest"  # update this

   Then deploy the pod:

   .. code-block:: yaml

      kubectl create -f keeper-mgmt-pod.yaml

3. Log into the maintenance pod and apply the migration:

   .. code-block:: bash
   
      kubectl exec keeper-mgmt -c uwsgi -i -t /bin/bash

   To apply the migration:

   .. code-block:: bash

      FLASK_APP=keeper flask db upgrade
   
   When the upgrade is complete, log out of the management pod's shell:

   .. code-block:: bash

      exit

4. Delete the management pod:

   .. code-block:: bash

      kubectl delete pod keeper-mgmt

5. Deploy the application.

   First update the uWSGI container's ``image`` name in :file:`keeper-deployment.yaml` to match the one used by the maintenance pod, and deploy it:

   .. code-block:: bash

      kubectl apply -f keeper-deployment.yaml

.. _gke-migrations-troubleshooting:

Troubleshooting
===============

Unexpected branched state
-------------------------

It's possible for Alembic to get into an unexpected branching state, producing an error message during a ``flask db upgrade`` like::

   alembic.util.exc.CommandError: Requested revision 1ba709663f26 overlaps with other requested revisions 0c0c70d73d4b

The ``flask db heads``, ``flask db branches``, and ``flask db current`` commands will show a normal, linear version history.
A true validation is to inspect the ``alembic_version`` table in the database.

Following :ref:`gke-cloudsql-connect`, log into the database and show the ``alembic_version`` table:

.. code-block:: sql

   use keeper;
   select * from alembic_version;

If more than one version row is present, then the table can be easily reset.
First, drop the ``alembic_version`` table:

.. code-block:: sql

   drop table alembic_version;

Then in the management pod, stamp the database version:

.. code-block:: bash

   FLASK_APP=keeper flask db stamp $VERSION

``$VERSION`` is the ID of the known current migration.
This creates a new ``alembic_version`` table with a single row specifying the current version.
Now the database upgrade can be retried.
