#######################################
Creating and Using a Staging Deployment
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
