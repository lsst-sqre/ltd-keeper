####################################
Configuring LTD Keeper on Kubernetes
####################################

In a production deployment, Keeper is configured entirely through environment variables (see :file:`config.py` in the Keeper repo).
The pod template files set these environment variables through `Kubernetes Secrets <http://kubernetes.io/docs/user-guide/secrets/>`_.
See the ``env`` section in :file:`kubernetes/keeper-pod.yaml`, for example.

The Keeper Git repository includes two secrets templates:

1. :file:`kubernetes/keeper-secrets.template.yaml` creates a secrets resource named ``keeper-secrets`` and is used to configure the Keeper Flask web app.
2. :file:`kubernetes/keeper-ingress-secrets.template.yaml` creates a secrets resource named ``keeper-ingress-secrets`` and is used to supply TLS certs to the Ingress resource.

Setting and Deploying Secrets
=============================

Secrets are set as key-value pairs in the ``data`` field of secrets YAML files.
For example:

.. code-block:: yaml

   apiVersion: v1
   kind: Secret
   metadata:
     name: keeper-secrets
   type: Opaque
   data:
     secret-key: aGVsbG8td29ybGQ=
     # ...

A Pod template file can reference this secret named ``secret-key`` in this ``keeper-secrets`` resource as:

.. code-block:: yaml

   apiVersion: v1
   kind: Pod
   # ...
   spec:
     containers:
       - name: uwsgi
         # ...
         env:
           - name: LTD_KEEPER_SECRET_KEY
             valueFrom:
               secretKeyRef:
                 name: keeper-secrets
                 key: secret-key
           # ...

Now the environment variable ``LTD_KEEPER_SECRET_KEY`` in the ``uwsgi`` container has the value from ``secret-key``.

.. _gke-encoding-secrets:

Encoding secrets
----------------

The values of secrets in the Secrets YAML files must be base64 encoded.
A convenient command for encoding a string (and copying it to the clipboard on OS X) is

.. code-block:: bash

   echo -n "secret-value" | base64 | pbcopy

Two recommendations for working with secrets files:

1. Do not work with YAML files directly in the Keeper Git repository; copy them out of the repo first into a working directory.

2. In the edited ``*-secrets.yaml`` file it can be useful to added the un-encoded value as a comment.

.. _gke-deploying-secrets:

Deploying secrets
-----------------

If the secrets file is named :file:`secrets.yaml`, it can be deployed with ``kubectl``:

.. code-block:: bash

   kubectl create -f secrets.yaml

You can review deployed secrets with:

.. code-block:: bash

   kubectl get secrets

And remove it:

.. code-block:: bash

   kubectl delete secret SECRETS_NAME

Note that containers, and other Kubernetes resources, only get secrets when they are first deployed.
You need to re-deploy the Pod to update environment variables in a container.

Keeper Configuration Reference
==============================

Keeper is configured through the following environment variables when run in a production context.

This section describes the :file:`kubernetes/keeper-secrets.template.yaml` file, which provides the ``keeper-secrets`` to set environment variables in the container running the Keeper Flask app.
In each block, the first name refers to a key in the secrets file, and the arrows points to the name of the environment variable that the Keeper Flask app uses to consume the secret.

``secret-key`` → ``LTD_KEEPER_SECRET_KEY``
   The secret key for authentication.

``db-url`` → ``LTD_KEEPER_DB_URL``
   URL of Keeper's SQL database.
   For SQLite, this is in the form ``'sqlite:////path/to/db.sqlite'`` for absolute paths.
   See the `SQLAlchemy Database Urls docs <http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls>`_ for more information.

   In the default deployment configuration, the SQLite database is stored in a persistent disk volume mounted at ``/var/lib/sqlite/``.

``default-user`` → ``LTD_KEEPER_BOOTSTRAP_USER``
   Username of the initial user for bootstrapping a Keeper DB.
   This bootstrap user is granted full API permissions.

``default-password`` → ``LTD_KEEPER_BOOTSTRAP_PASSWORD``
   Password for the bootstrap user.

``server-name`` → ``LTD_KEEPER_URL``
   The externally-facing domain name of the Keeper API server (e.g., ``ltd-keeper.lsst.codes``.
   For a Kubernetes deployment this is the domain name attached to the external IP of the Ingress resource.

``aws-id`` → ``LTD_KEEPER_AWS_ID``
   Amazon Web Services key ID.
   This key must have access to AWS Route 53 and S3 for the documentation domains and storage bucket, respectively, used by LSST the Docs.

``aws-secret`` → ``LTD_KEEPER_AWS_SECRET``
   Amazon Web Services secret corresponding to ``LTD_KEEPER_AWS_ID``.
