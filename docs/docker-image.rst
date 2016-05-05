#############
Docker Images
#############

LTD Keeper should be deployed as a Docker container in production.
This page describes how to build new Docker images as part of the development process.

See also :doc:`compose` for information on using the containers locally and the :ref:`Operations Guide <ops-guide>` for how to use the LTD Keeper docker image in production.

Published Images
================

LTD Keeper's Docker images are published on Docker Hub under the `lsstsqre <https://hub.docker.com/u/lsstsqre>`_ organization (LSST SQuaRE).
Relevant images are:

- ``lsstsqre/ltd-keeper:latest`` --- Created by the Dockerfile in this `github.com/lsst-sqre/ltd-keeper <https://github.com/lsst-sqre/ltd-keeper>`_ repository. This deploys LTD Keeper as a uWSGI application.
- ``lsstsqre/nginx-python:compose`` --- An Nginx Proxy for LTD Keeper containers to be used in a Docker Compose environment (see :doc:`compose`). The related Dockerfile can be found in `github.com/lsst-sqre/nginx-python-docker <https://github.com/lsst-sqre/nginx-python-docker>`_.
- ``lsstsqre/nginx-python:k8s`` --- An Nginx Proxy for LTD Keeper containers to be used in a Kubernetes environment (see :doc:`gke-deploy`). The related Dockerfile can be found in `github.com/lsst-sqre/nginx-python-docker <https://github.com/lsst-sqre/nginx-python-docker>`_.


Building and Publishing the Keeper Docker Image
===============================================

To publish a revised Keeper Docker image, run these commands from the LTD Keeper repository.

.. code-block:: bash

   docker build -t lsstsqre/ltd-keeper:latest .
   docker push lsstsqre/ltd-keeper:latest
