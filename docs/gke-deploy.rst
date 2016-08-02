#############################
Initial Kubernetes Deployment
#############################

Prerequisites
=============

The steps assume the follow steps described on previous pages have been accomplished:

1. Created the project on Google Cloud Platform and configured the ``gcloud`` and ``kubectl`` apps.

2. Created the cluster and persistent storage.

3. Customized the :file:`kubernetes/keeper-secrets.template.yaml` and :file:`kubernetes/ssl-proxy-secrets.template.yaml` files with the appropriate configurations and TLS certs.

Step 1. Deploy Secrets
======================

Deploy the secrets with:

.. code-block:: bash

   kubectl create -f keeper-secrets.yaml
   kubectl create -f ssl-proxy-secrets.yaml
   kubectl create -f cloudsql-secrets.yaml

You can see they have been deployed with:

.. code-block:: bash

   kubectl get secrets

Step 2. Deploy Services
=======================

.. code-block:: bash

   kubectl create -f ssl-proxy-service.yaml
   kubectl create -f keeper-service.yaml

Check for the external IP of the ssl-proxy-service with:

.. code-block:: bash

   kubectl get services

Set the domain's A record to this IP.
This domain was specified as ``server-name`` in :file:`keeper-secrets.yaml`.

Step 3. Deploy the SSL Proxy
============================

.. code-block:: bash

   kubectl create -f ssl-proxy.yaml

Check that the replication controller exists:

.. code-block:: bash

   kubectl get rc

And that the nginx-ssl-proxy pod exists:

.. code-block:: bash

   kubectl get pods

Step 4. Deploy the Maintenance Pod
==================================

We use a standalone maintenance pod to initialize the database.

This pod needs to run as root, so *uncomment* the ``securityContext`` section in ``keeper-mgmt-pod.yaml``.

Deploy the pod:

.. code-block:: bash

   kubectl create -f keeper-mgmt-pod.yaml

Watch for the pod to be created with ``kubectl get pods``.
Once it's ready, log in:

.. code-block:: bash

   kubectl exec keeper-mgmt -c uwsgi -i -t /bin/bash

From the uwsgi container's prompt,

.. code-block:: bash

   ./run.py createdb
   ./run.py init

This will:

1. Create tables in a blank database.
2. Seed an administrative user account (based on ``default-user`` and ``default-password`` fields in the ``keeper-secrets`` resource).

``exit`` from the ``keeper-mgmt`` shell and then take down the maintenance pod:

.. code-block:: bash

   kubectl delete pod keeper-mgmt

Wait for the pod to terminate by watching ``kubectl get pods``.

Step 5. Deploy LTD Keeper
=========================

As an API server, LTD Keeper is run as a *deployment*, which is Kubernetes short-hand for a replication controller with Pod templates.

To create a new deployment:

.. code-block:: bash

   kubectl create -f keeper-deployment.yaml

Check that the replication controller is up:

.. code-block:: bash

   kubectl get rc

Verify that the pod is deployed with:

.. code-block:: bash

   kubectl get pods

You can know verify that Keeper is serving over HTTPS:

   curl https://keeper.lsst.codes/products/

(Substitute your deployment hostname as necessary.)
