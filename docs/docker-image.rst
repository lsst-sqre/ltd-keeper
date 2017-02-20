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


Building and Publishing the Keeper Docker Image
===============================================

To publish a revised Keeper Docker image, run these commands from the LTD Keeper repository.

.. code-block:: bash

   git tag -s YYYYMMDD-N
   docker build -t lsstsqre/ltd-keeper:YYYYMMDD-N .
   docker push lsstsqre/ltd-keeper:YYYYMMDD-N

Replace ``YYYYMMDD-N`` with the current date and incrementing number.
Tagging images this way makes it obvious how to roll-back a deployment.

For full 'releases' we may use conventional 'semvar' tags, but have not done so yet.
