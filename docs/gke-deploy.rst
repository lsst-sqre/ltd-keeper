#############################
Initial Kubernetes Deployment
#############################

Prerequisites
=============

The steps assume the follow steps described on previous pages have been accomplished:

1. Created the project on Google Cloud Platform and configured the ``gcloud`` and ``kubectl`` apps.

2. Created the cluster and persistent storage.

3. Customized the :file:`kubernetes/keeper-secrets.template.yaml` and :file:`kubernetes/keeper-ingress-secrets.template.yaml` files with the appropriate configurations and TLS certs.

Step 1. Deploy Secrets
======================

Deploy the secrets with:

.. code-block:: bash

   kubectl create -f keeper-secrets.yaml

You can see they have been deployed with:

.. code-block:: bash

   kubectl get secrets

Step 2. Deploy the Maintenance Pod
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

   ./run.py init
   chown -R uwsgi:uwsgi_grp /var/lib/sqlite

This will:

1. Create the database in :file:`/var/lib/sqlite` (set in the ``keeper-secrets.yaml`` file).
2. Grant ownership to the ``uwsgi`` over the database.
   Normally we run the uwsgi container with a uwsgi, not root, user.

``exit`` from the keeper-mgmt prompt and take down the maintenance pod:

.. code-block:: bash

   kubectl delete pod keeper-mgmt

Wait for the pod to terminate by watching ``kubectl get pods``.

Step 3. Deploy the Keeper Pod
=============================

.. code-block:: bash

   kubectl create -f keeper-pod.yaml

Verify that the pod is deployed with

.. code-block:: bash

   kubectl get pods

Step 4. Deploy the LoadBalancer Service
=======================================

.. code-block:: bash

   kubectl create -f keeper-service.yaml

View the services with

.. code-block:: bash

   » kubectl get services
   NAME         CLUSTER-IP     EXTERNAL-IP     PORT(S)   AGE
   keeper       10.63.252.59   104.154.19.40   80/TCP    1m
   kubernetes   10.63.240.1    <none>          443/TCP   1h

Note that it may take a while for the keeper service to get an external IP.

Step 5. Configure DNS
=====================

Create a CNAME record so that the domain name configured with the ``server-name`` secret in :file:`keeper-secrets.yaml`.
