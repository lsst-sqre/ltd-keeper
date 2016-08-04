############################################
Setting up a Google Container Engine Cluster
############################################

To deploy LTD Keeper we recommend using Docker Containers orchestrated by `Kubernetes <http://kubernetes.io>`_.
Although Kubernetes can be hosted on any public or private cloud, `Google Container Engine <https://cloud.google.com/container-engine/>`_ provides a convenient platform to run Kubernetes.
This page will describe how to install the Google command line apps, configure them, and create a cluster.

.. _gke-create-gcp-project:

Setup the Cloud Platform Project
================================

First, you need to create a project on Google Cloud Platform.
Follow `Google's Getting Started instructions <https://cloud.google.com/container-engine/docs/before-you-begin>`_ to:

1. Create a Project on Google Cloud Platform. Note that you can have multiple clusters in a Project; projects are mostly to ease administration, access, and billing.

2. Enable the Container Engine API.

3. Install ``gcloud`` (CLI for Google Cloud Platform) and ``kubectl`` (CLI for Kubernetes).

4. Set your ``gcloud`` defaults to use the project's ID and set a default zone. For example:

   .. code-block:: bash
   
      gcloud config set project plasma-geode-127520
      gcloud config set compute/zone us-central1-b

.. _gke-create-cluster:

Create the Cluster
==================

Now that ``gcloud`` is configured to use the correct Project, in the right zone, we can create a cluster of Google Compute Engine nodes.

Note that Kubernetes clusters need to be homogeneous; you cannot match different machine types.\ [#machine-types]_
`Google has a page listing the specs and pricing of instance types. <https://cloud.google.com/compute/docs/machine-types>`_.
Once a cluster is created you can easily expand it by adding nodes (or decrease the number of nodes).

.. [#machine-types] https://medium.com/@betz.mark/comparing-amazon-elastic-container-service-and-google-kubernetes-1c63fbf19ccd#.sc5mywy0s

For development, a single node cluster with the ``g1-small`` machine type is sufficient.
For example:

.. code-block:: bash

   gcloud container clusters create lsst-the-docs \
       --num-nodes 1 \
       --machine-type g1-small

Then make this ``lsst-the-docs`` cluster the default and obtain the credentials:

.. code-block:: bash

   gcloud config set container/cluster lsst-the-docs
   gcloud container clusters get-credentials lsst-the-docs

You can later rescale this cluster.
For example:

.. code-block:: bash

   gcloud container clusters resize lsst-the-docs --size=2

Often it's necessary to rescale the cluster when pods can't be scheduled because the existing nodes are fully utilized.

.. _gke-config-checklist:

Checklist for other users to access the cluster
===============================================

If you just need to work with a pre-existing project and cluster, configure ``gcloud`` and ``kubectl`` as follows:

1. `Install gcloud <https://cloud.google.com/container-engine/docs/before-you-begin#install_the_gcloud_command-line_interface>`_ and `kubectl <https://cloud.google.com/container-engine/docs/before-you-begin#install_kubectl>`_

2. Set the ``gcloud`` defaults and get credentials for the cluster:

   .. code-block:: bash

      gcloud config set project plasma-geode-127520
      gcloud config set compute/zone us-central1-b
      gcloud config set container/cluster lsst-the-docs
      gcloud container clusters get-credentials lsst-the-docs

You can review your ``gcloud`` default configurations with:

.. code-block:: bash

   gcloud config list

Next, :doc:`configure a Cloud SQL instance <gke-cloudsql>`.
