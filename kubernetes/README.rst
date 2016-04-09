########################################
Google Container Engine Deployment Notes
########################################

Set up container engine environment
===================================

Create a project and enable billing for it.

Follow https://cloud.google.com/container-engine/docs/before-you-begin to set up ``gcloud`` command line interface.

Set your gcloud defaults to use the project's ID and set a default zone.

.. code-block:: bash

   gcloud config set project plasma-geode-127520
   gcloud config set compute/zone us-central1-b

See https://cloud.google.com/compute/docs/zones#available for a list of zones; ``us-central1-b`` has newer processors.

Create the cluster
==================

Create a cluster, get credentials for it, and make it the default for ``gcloud``:

.. code-block:: bash

   gcloud container clusters create lsst-the-docs \
       --num-nodes 1 \
       --machine-type g1-small
   gcloud config set container/cluster lsst-the-docs
   gcloud container clusters get-credentials lsst-the-docs

Create storage for Keeper
=========================

At the moment Keeper uses sqlite as its database.
We want this DB to persist between pods, so we'll create a persistent disk in Google Compute Engine

.. code-block:: bash

   gcloud compute disks create --size 1GB keeper-disk

.. note::

   Having such a small (less than 200 GB) disk degraded I/O performance on GCE.
   See https://developers.google.com/compute/docs/disks#pdperformance.

Create the LoadBalancer Service for Keeper
==========================================

.. code-block:: bash

   kubectl create -f keeper-service.yaml

View the services with

.. code-block:: bash

   » kubectl get services
   NAME         CLUSTER-IP     EXTERNAL-IP     PORT(S)   AGE
   keeper       10.63.252.59   104.154.19.40   80/TCP    1m
   kubernetes   10.63.240.1    <none>          443/TCP   1h

Note that it may take a while for the keeper service to get an external IP.

Initialization of Secrets and the Database
==========================================

Update container images
-----------------------

By default we deploy the `lsstsqre/ltd-keeper:latest <https://hub.docker.com/r/lsstsqre/ltd-keeper/>`_ image.
Keeper can update the Keeper container by running:

.. code-block:: bash

   docker build -t lsstsqre/ltd-keeper:latest .
   docker push lsstsqre/ltd-keeper:latest

Configure and deploy secrets
----------------------------

Modify the ``keeper-secrets.template.yaml`` replication controller definition file with the actual Keeper pod configuration.
Each value must be base64-encoded.

Deploy the secrets with:

.. code-block:: bash

   kubectl create -f keeper-secrets.yaml

You can see they have been deployed with:

.. code-block:: bash

   kubectl get secrets

Deploy the Keeper Maintenance Pod and initialize the database
-------------------------------------------------------------

We'll use a standalone maintenance pod to initialize the database.

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

1. Create the database in /var/lib/sqlite (set in the ``keeper-secrets.yaml`` file).
2. Grant ownership to the ``uwsgi`` over the database. Normally we run the uwsgi container with a uwsgi, not root, user.

``exit`` from the keeper-mgmt prompt and take down the maintenance pod:

.. code-block:: bash

   kubectl delete pod keeper-mgmt

Wait for the pod to terminate by watching ``kubectl get pods``.

Deploy a Keeper API server pod
==============================

.. code-block:: bash

   kubectl create -f keeper-pod.yaml

****

Deploy the keeper Pod Replication Controller
============================================

.. warning::

   We can't use a replication controller since the current pod template needs an attached persistent storage volume.
   We can use a replication controller-based setup once we switch to a networked database.

.. code-block:: bash

   kubectl create -f keeper-controller.yaml

Deploy the Ingress resource
===========================

.. warning::

   This section is in work.

First we need to set a firewall rule manually, as mentioned in http://kubernetes.io/docs/user-guide/ingress/#prerequisites to the service built previously.

.. code-block:: bash

   export TAG=$(basename `gcloud container clusters describe lsst-the-docs --zone us-central1-b | grep gke | awk '{print $2}'` | sed -e s/grp/node/)
   export NODE_PORT=$(kubectl get -o jsonpath="{.spec.ports[0].nodePort}" services echoheaders)

.. note::
   
   Substitute the cluster name, zone as necessary and service name as neccesary.

   Also note that I modified the last sed command to substitute ``grp`` rather than ``group``.

.. note::

   The k8s docs for ingress talk about need to make a replication controller for ingress first; I think gke comes with an ingress replication controller?
