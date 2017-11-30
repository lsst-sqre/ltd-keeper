#######################################
Creating and using a staging deployment
#######################################

When working on LTD Keeper, it's sometimes useful to create a separate Kubernetes deployment for testing that's isolated from production.
For example, a staging deployment can be used to test breaking changes like SQL migrations.
Ideally this would be an automated integration test.
But for now, this page gives a playbook for creating an isolated staging deployment.

.. _gke-staging-db:

Duplicating the production database
===================================

.. _gke-staging-db-create-instance:

Creating the staging CloudSQL instance
--------------------------------------

Create a CloudSQL instance for staging called ``ltd-sql-staging``, if one is not already available.

1. Visit the project's CloudSQL console dashboard, https://console.cloud.google.com/sql/, and click **Create instance**.
2. Choose a second generation of CloudSQL.
3. Configure to match the production CloudSQL instance:

   - Name: ``ltd-sql-staging``.
   - DB version: MySQL 5.6.
   - Region: ``us-central1-b``.
   - Type: ``db-g1-small``.
   - Disk: 10 GB.
   - Disable backups and binary logging (not needed for staging).

.. note::

   This staging DB inherits the credentials from the production database.
   There's no need to create a new root user password.

.. _gke-staging-db-restore:

Restore the production DB backup to the staging DB
--------------------------------------------------

Follow `CloudSQL documentation on restoring to a different instance <https://cloud.google.com/sql/docs/mysql/backup-recovery/restoring#restorebackups-another-instance>`_.

The **backup** should be a recent one from the production database.
The **target instance** is ``ltd-sql-staging``.
Since this is a temporary staging DB, it's safe to overwrite any existing data.

You can connect to this staging database by following:

1. :ref:`gke-cloudsql-proxy`.
2. :ref:`gke-cloudsql-connect`.

.. _gke-staging-db-further-reading:

Further reading
---------------

- `Tips on restoring to a different instance <https://cloud.google.com/sql/docs/mysql/backup-recovery/restore#tips-restore-different-instance>`_.
- `Tips on restoring with CloudSQL <https://cloud.google.com/sql/docs/mysql/backup-recovery/restore#tips-restore>`_.

.. _gke-staging-namespace:

Creating and using a Kubernetes namespace for staging
=====================================================

Create a namespace
------------------

Check what namespaces currently exist in the cluster:

.. code-block:: bash

   kubectl get namespaces

Currently, production is deployed to the ``default`` namespace; we use an ``ltd-staging`` (or similar) namespace for integration testing.
To create the ``ltd-staging`` namespace using the :file:`kubernetes/ltd-staging-namespace.yaml` resource template in the Git repository:

.. code-block:: bash

   kubectl create -f ltd-staging-namespace.yaml

Confirm that an ``ltd-staging`` namespace exists:

.. code-block:: bash

   kubectl get namespaces --show-labels

Create the context
------------------

Contexts allow you to switch between clusters and namespaces when working with ``kubectl``.
First, look at the existing contexts (these are configured locally):

.. code-block:: bash

   kubectl config get-contexts

If there's only a context for the ``lsst-the-docs`` cluster and default namespace, then we can create a context for the ``ltd-staging`` namespace.

.. code-block:: bash

   kubectl config set-context ltd-staging --namespace=ltd-staging --cluster=$CLUSTER_NAME --user=$CLUSTER_NAME

where ``$CLUSTER_NAME`` are the same as that for the existing default context.

It's also convenient to create a name for the default namespace:

.. code-block:: bash

   kubectl config set-context ltd-default --cluster=$CLUSTER_NAME --user=$CLUSTER_NAME

Switch to the staging context
-----------------------------

.. code-block:: bash

   kubectl config use-context ltd-staging

You can confirm what namespace you're working in with:

.. code-block:: bash

   kubectl config current-context

Further reading
---------------

- `Kubernetes namespaces walkthrough <https://kubernetes.io/docs/admin/namespaces/walkthrough/>`_.

.. _gke-staging-deployment:

Deploying to the staging namespace
==================================

LTD Keeper can be deployed into the ``ltd-staging`` namespace using the same pattern described in :doc:`gke-config` and :doc:`gke-deploy`.
Some modifications, described below, are needed to re-configure the deployment for staging.

Modifying configuration and secrets
-----------------------------------

Secrets and other resources need to be customized for the staging namespace:

- Modifications to :file:`kubernetes/keeper-secrets-staging.yaml`:

  - ``db-url`` should point to the new ``ltd-sql-staging`` database.

- Modifications to :file:`kubernetes/keeper-config-staging.yaml`:

  - ``server-name`` should point to a staging URL, like ``keeper-staging.lsst.codes``.
    Remember to create a new DNS record pointing to the ``nginx-ssl-proxy``.

  - ``cloud-sql-instance``: should point to the new ``ltd-sql-staging`` database.

.. note::

   It may be necessary to update :file:`kubernetes/ssl-proxy-secrets.yaml` if you aren't using a wildcard cert.

.. warning::

   With the staging deployment, as currently implemented, the database is independent, but resources in the S3 bucket **are not**, since the S3 bucket is specified in DB tables that are replicated from the production DB.
