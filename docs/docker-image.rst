#############
Docker images
#############

LTD Keeper is deployed in production as a Docker container through Kubernetes.
This page describes how to build new Docker images as part of the development process.

See the :ref:`Operations Guide <ops-guide>` for how to use the LTD Keeper Docker image in production.

Published images
================

LTD Keeper's Docker images are published on Docker Hub under the `lsstsqre <https://hub.docker.com/u/lsstsqre>`_ organization (LSST SQuaRE).

lsstsqre/ltd-keeper
-------------------

The primary image is ``lsstsqre/ltd-keeper``, created from the Dockerfile in `LTD Keeper's repository. <https://github.com/lsst-sqre/ltd-keeper>`__.
This Docker image makes LTD Keeper available as a uWSGI application on port 3031.

The ``lsstsqre/ltd-keeper`` is build automatically through `Travis CI <https://travis-ci.org/lsst-sqre/ltd-keeper>`__.
The key tags are:

- ``latest``: built from the ``master`` branch of the GitHub repository.
- ``X.Y.Z``: semantically-versioned releases, corresponding to tags in the GitHub repository.
- ``tickets-DM-N``: built from LSST Data Management development branches.

lsstsqre/nginx-python:k8s
-------------------------

This is an Nginx Proxy for LTD Keeper containers to be used in a Kubernetes pod (see :doc:`gke-deploy`).
The related Dockerfile can be found in `github.com/lsst-sqre/nginx-python-docker <https://github.com/lsst-sqre/nginx-python-docker>`_.

Building and publishing the lsstsqre/ltd-keeper Docker image
============================================================

For local development
---------------------

During development, you can make a local Docker image:

.. code-block:: bash

   make image

This image is tagged as ``lsstsqre/ltd-keeper:build``, but is not immediately pushed to Docker Hub.

For development on Docker Hub
-----------------------------

Whenever you push commits to a branch on GitHub, Travis CI builds and pushes a new image that is tagged corresponding to the branch name.
Note the following rules:

- "``/``" characters are replaced by "``-``."
  For example, a ``tickets/DM-N`` branch is tagged as ``lsstsqre/ltd-keeper:tickets-DM-N``.

- The ``master`` branch is tagged as ``lsstsqre/ltd-keeper:tickets-DM-N``.

For release
-----------

Released Docker images use semantic version labels.
Make these images by tagging the Git repository:

.. code-block:: bash

   git tag -s X.Y.Z -m "X.Y.Z"
   git push --tags

Travis CI builds and publishes the corresponding ``lsstsqre/ltd-keeper:X.Y.Z`` image.
