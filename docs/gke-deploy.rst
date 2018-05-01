#############################
Initial Kubernetes deployment
#############################

Prerequisites
=============

The steps assume the follow steps described on previous pages have been accomplished:

1. Created the project on Google Cloud Platform and configured the ``gcloud`` and ``kubectl`` apps.

2. Created the cluster and persistent storage.

3. Customized the configuration files, see :doc:`gke-config`.

Step 1. Deploy configurations
=============================

Deploy the configurations with:

.. code-block:: bash

   kubectl apply -f keeper-secrets-prod.yaml
   kubectl apply -f keeper-config-prod.yaml
   kubectl apply -f keeper-tls-secrets.yaml
   kubectl apply -f cloudsql-secrets.yaml

You can see they have been deployed with:

.. code-block:: bash

   kubectl get secrets
   kubectl get configmaps

Step 2. Deploy redis
====================

.. code-block:: bash

   kubectl apply -f redis-deployment.yaml
   kubectl apply -f redis-service.yaml

Step 3. Deploy the maintenance pod
==================================

We use a standalone maintenance pod to initialize the database.

Deploy the pod:

.. code-block:: bash

   kubectl create -f keeper-mgmt-pod.yaml

Watch for the pod to be created with ``kubectl get pods``.
Once it's ready, log in:

.. code-block:: bash

   kubectl exec keeper-mgmt -c uwsgi -i -t /bin/bash

From the uwsgi container's prompt:

.. code-block:: bash

   FLASK_APP=keeper flask createdb
   FLASK_APP=keeper flask init

This will:

1. Create tables in a blank database.
2. Seed an administrative user account (based on ``default-user`` and ``default-password`` fields in the ``keeper-secrets`` resource).

``exit`` from the ``keeper-mgmt`` shell and then take down the maintenance pod:

.. code-block:: bash

   kubectl delete pod keeper-mgmt

Wait for the pod to terminate by watching ``kubectl get pods``.

Step 4. Deploy LTD Dasher
=========================

Deploy LTD Dasher into the same namespace.
See https://github.com/lsst-sqre/ltd-dasher.

Step 5. Deploy LTD Keeper
=========================

As an API server, LTD Keeper is run as a *deployment*, which is Kubernetes short-hand for a replication controller with Pod templates.

The application server and Celery worker pool are separately-managed deployments:

.. code-block:: bash

   kubectl create -f keeper-deployment.yaml
   kubectl create -f keeper-worker-deployment.yaml

Watch for the deployment to complete:

.. code-block:: bash

   kubectl get deployments -w

Step 6. Deploy services
=======================

.. code-block:: bash

   kubectl apply -f keeper-service.yaml

Step 7. Deploy the Ingress
==========================

.. code-block:: bash

   kubectl apply -f ingress.yaml

Watch for the ``keeper`` ingress to start up:

.. code-block:: bash

   kubectl get ingress -w

Once an external IP appears, set the domain's ``A`` record to that IP.

You can now verify that Keeper is serving over HTTPS:

.. code-block:: bash

   curl https://keeper.lsst.codes/

(Substitute your deployment hostname as necessary.)
