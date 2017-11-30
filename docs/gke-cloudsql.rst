##########################
Configure Google Cloud SQL
##########################

When running LTD Keeper from the Google Container Engine, it makes sense to use Google's Cloud SQL hosted database service.
Separating Keeper's state from the application grants us operational flexibility to scale and upgrade the application through Kubernetes.

Google Cloud SQL manages the MySQL server, along with backups and fail-over, allowing pods and the LTD Keeper application itself to be stateless and therefore scalable.

LTD Keeper uses a 2nd generation high-availability Cloud SQL instance, which can be created by following Google's documentation at https://cloud.google.com/sql/docs/create-instance.

Enable the Cloud SQL API
========================

First, the Cloud SQL API may need to be explicitly enabled.
This can be done from the Google Cloud console's API section.

Create a High-Availabilty SQL Instance
======================================

Create a master instance named ``ltd-sql`` using the :command:`gcloud` tool:

.. code-block:: bash

   gcloud sql instances create ltd-sql-1 --tier=db-g1-small --activation-policy=ALWAYS

Then set the root password for this instance:

.. code-block:: bash

   gcloud sql instances set-root-password ltd-sql-1 --password [PASSWORD]

Next, follow instructions at https://cloud.google.com/sql/docs/configure-ha to create a high-availability instance.
A high-availability SQL instance creates a fail-over node that continuously replicates the master.

You can also enable automated backups from the instance's page on the Google Cloud console.

Create a Service Account
========================

.. note::

   This step may not longer be necessary with Cloud SDK authentication and automatic service discovery.

To authenticate to the Cloud SQL instance, we need to create a Google Cloud Service Account.

Create a new Service Account from the IAM & Admin section of the Google Cloud console.

Name the Service Account ``sql-proxy-service`` and request a JSON credentials file.
This JSON file will be used directly with the Cloud SQL proxy and also to build configuration secrets.

See `Google's documentation for complete steps on creating a Service Account <https://cloud.google.com/sql/docs/sql-proxy#create-service-account>`__.

.. _gke-cloudsql-proxy:

Install and Run the Cloud SQL Proxy
===================================

LTD operators should install the `Cloud SQL Proxy <https://cloud.google.com/sql/docs/sql-proxy>`_ locally to access and administer the Cloud SQL instance.

Assuming that Go is installed:

.. code-block:: bash

   go get github.com/GoogleCloudPlatform/cloudsql-proxy/cmd/cloud_sql_proxy

Create a convenient directory where a unix socket can be created:

.. code-block:: bash

   mkdir cloudsql
   sudo chmod 777

And run the proxy:

.. code-block:: bash

   $GOPATH/bin/cloud_sql_proxy -dir=cloudsql

.. note::

   Alternatively, a Service Account credential can be used:

   .. code-block:: bash
   
      $GOPATH/bin/cloud_sql_proxy -dir=cloudsql -instances=PROJECT:REGION:ltd-sql-1 --credential_file=service_account.json
   
   Replace ``PROJECT`` and ``REGION`` with the Google Cloud project's name and default region (specified previously in :doc:`gke-setup`).

   ``service_account.json`` is the path to the service account JSON credentials file that was downloaded previously.

See the `github.com/GoogleCloudPlatform/cloudsql-proxy <https://github.com/GoogleCloudPlatform/cloudsql-proxy>`_ repository for further details.

.. _gke-cloudsql-connect:

Connect to the Cloud SQL Instance and Create a keeper Database
==============================================================

With the Cloud SQL Proxy running in one terminal session, run a :command:`mysql` client in other.

.. code-block:: bash

   mysql -u root -p -S ./cloudsql/PROJECT:REGION:ltd-sql-1

and enter the databases' root password created previously.

While logged into the database, create a DB specifically for LTD Keeper:

.. code-block:: text

   mysql> create database keeper;
   Query OK, 1 row affected (0.10 sec)
   
   mysql> show databases;
   +--------------------+
   | Database           |
   +--------------------+
   | information_schema |
   | keeper             |
   | mysql              |
   | performance_schema |
   +--------------------+
   4 rows in set (0.08 sec)

You may now ``exit`` from the :command:`mysql` terminal and close the proxy connection (control-C).

Next, :doc:`create configuration secrets in Kubernetes <gke-config>`.
