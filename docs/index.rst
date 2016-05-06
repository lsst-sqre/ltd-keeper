##########
LTD Keeper
##########

LTD Keeper is the backend database and application that runs LSST the Docs.
You can interact with the Keeper through its RESTful HTTP API.

For more information about LSST the Docs, see `SQR-006: Documentation Deployment Service for LSST's Eups-based Software <http://sqr-006.lsst.io>`_.

.. toctree::
   :caption: HTTP API
   :name: http-api
   :maxdepth: 1

   api_intro
   auth
   products
   builds
   editions

.. toctree::
   :caption: Development
   :name: dev-guide
   :maxdepth: 1

   install
   docker-image
   compose
   dev-migrations

.. toctree::
   :caption: Operations
   :name: ops-guide
   :maxdepth: 1

   gke-arch
   gke-setup
   gke-config
   gke-deploy
   gke-update
   gke-migrations
