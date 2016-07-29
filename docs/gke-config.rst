####################################
Configuring LTD Keeper on Kubernetes
####################################

In a production deployment, Keeper is configured entirely through environment variables (see :file:`config.py` in the Keeper repo).
The pod template files set these environment variables through `Kubernetes Secrets <http://kubernetes.io/docs/user-guide/secrets/>`_.
See the ``env`` section in :file:`kubernetes/keeper-pod.yaml`, for example.

The Keeper Git repository includes three secrets templates:

1. :file:`kubernetes/keeper-secrets.template.yaml` creates a secrets resource named ``keeper-secrets`` and is used to configure the Keeper Flask web app.
2. :file:`kubernetes/ssl-proxy-secrets.template.yaml` creates a secrets resource named ``ssl-proxy-secret`` and is used to supply TLS certs to the Nginx proxy service.
3. :file:`kubernetes/cloudsql-secrets` creates a secrets resource named ``sql-creds`` containing credentials for the Google Cloud SQL instance. 

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

To encode a file:

.. code-block:: bash

   base64 -i secret.key | pbcopy

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
   For a Cloud SQL instance, this URL has the form: ``mysql+pymysql://root:PASSWORD@/keeper?unix_socket=/cloudsql/PROJECT:REGION:ltd-sql-1``.
   Replace PASSWORD with the database password (see :doc:`gke-cloudsql`), along with PROJECT and REGION with the Cloud project details (see :doc:`gke-setup`).
   Remember that this is a URI, so any unusual characters (particularly in the password) must be escaped/quoted.
   Python's `urllib.parse.quote <https://docs.python.org/3/library/urllib.parse.html#urllib.parse.quote>`__ can help prepare a URL.
   See the `SQLAlchemy Database Urls docs <http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls>`_ for more information.

   Finally, note that we recommend the ``pymysql`` 'dialect' MySQL.
   The PyMySQL package is automatically installed with LTD Keeper in its docker container.

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

``fastly-id`` → ``LTD_KEEPER_FASTLY_ID``
   Fastly service ID.

``fastly-key`` → ``LTD_KEEPER_FASTLY_KEY``
   Fastly API key.

Nginx SSL Proxy Configuration Reference
=======================================

This section describes the :file:`kubernetes/ssl-proxy-secrets.template.yaml`, which provides ``ssl-proxy-secret`` to the ssl-proxy pods.
These secrets includes the SSL certificate, SSL private key, and a DHE parameter.

``proxycert``
   The SSL certificate (combined with the intermediate).
   Encode this value with:

   .. code-block:: bash

      base64 -i example_org.crt | pbcopy

``proxykey``
   The SSL private key.

   .. code-block:: bash

      base64 -i example_org.key | pbcopy

``dhparam``
   The DHE parameter.

   .. code-block:: bash

      openssl dhparam -out dhparam.pem 2048
      base64 -i dhparam.pem

Cloud SQL Proxy Configuration Reference
=======================================

This section describes :file:`kubernetes/cloudsql-secrets.yaml`, which provides the ``cloudsql-creds`` to ``cloudsql-proxy`` containers.

``file.json``
   This is a base64-encoded JSON service account credential file. A Google Cloud Platform Service Account was created earlier in :doc:`gke-cloudsql`.

   .. code-block:: bash

      base64 -i credentials.json | pbcopy

Further documentation for the Cloud SQL Proxy can be found in the `github.com/GoogleCloudPlatform/cloudsql-proxy <https://github.com/GoogleCloudPlatform/cloudsql-proxy>`__ repository's README.
