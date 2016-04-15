###############################
Development with Docker Compose
###############################

Docker Compose_ is a tool for running multi-container applications for local development.
In production, LTD Keeper doesn't simply run on its own.
Instead we use nginx_ as a reverse proxy to uWSGI, which in turn serves the LTD Keeper Flask app.
In keeping with the microservices model of containers, nginx_ is deployed in a separate container from the uWSGI and LTD Keeper applications.
Compose_ allows us to run this multi-container application local to simulate a multi-container production deployment.

Getting Started
===============

You will need to install Docker installed in your development environment, specifically: Docker Engine, Docker Machine and Docker Compose.

For Mac developers, `Docker Toolkit <https://www.docker.com/products/docker-toolbox>`_ is what you want.
Follow their `Getting Stared guide <http://docs.docker.com/mac/started/>`_ to setup a local Docker host.
In your terminal sessions set up your environment via

.. code-block:: bash

   eval $(docker-machine env default)

Building and Running LTD Keeper
===============================

Cloning the nginx-python-docker and ltd-keeper repos
----------------------------------------------------

By default, we use Docker Compose to automatically build containers for us.
You'll need to have the `lsst-sqre/nginx-python-docker`_ container cloned alongside this `lsst-sqre/ltd-keeper`_ repository:

.. code-block:: bash

   git clone https://github.com/lsst-sqre/nginx-python-docker.git
   git clone https://github.com/lsst-sqre/ltd-keeper.git
   cd ltd-keeper

Start the application
---------------------

Inside the ``ltd-keeper/`` repository:

.. code-block:: bash

   docker-compose up -d

This does the following things:

1. Looks at the :file:`docker-compose.yaml` file for container configuration.
2. Builds the ``lsstsqre/ltd-keeper:latest`` image from the Dockerfile in this ``ltd-keeper`` repository and run it. This container runs LTD Keeper behind uWSGI.
3. Builds the ``lsstsqre/nginx-python-docker:latest`` image from the Dockerfile in the cloned ``nginx-python-docker`` repository. This container runs nginx as a reverse proxy to a uWSGI application.
4. Sets up the container cluster network, specifically opening port 3031 on the uWSGI container and exposing port 80 on the nginx container to the world (i.e., your development machine).
5. Runs the cluster in the background. Below we'll see commands to manage the cluster.

You can test that the application is running::

   http GET http://`docker-machine ip`:80/products/

This command assumes you've installed `httpie <http://httpie.org/>`_, which is a great HTTP client.
The ``docker-machine ip`` provides the local IP of the Docker machine running the application containers.

Commands to inspect the application
-----------------------------------

``docker images``
  This will show any images on your system, including the ones just build by ``docker-compose`` for your.

``docker-compose logs``
   This will show logs from all containers in the cluster

``docker ps``
   This will show all running containers and metadata about them.

``docker exec -ti <container id> /bin/bash``
   This allows you to log into a bash shell of a running container. In the above command, replace ``<container id>`` with an ID from ``docker ps``.

Cleanup
-------

To stop the application:

.. code-block:: bash

   docker-compose down

You can additionally remove the built images via

.. code-block:: bash

   rmi <IMAGE ID>

where ``<IMAGE ID>`` should be replace with a value from the ``docker images`` command.

.. _Compose: https://www.docker.com/products/docker-compose
.. _nginx: http
.. _`lsst-sqre/ltd-keeper`: https://github.com/lsst-sqre/ltd-keeper
.. _`lsst-sqre/nginx-python-docker`: https://github.com/lsst-sqre/nginx-python-docker
