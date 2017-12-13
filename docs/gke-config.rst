####################################
Configuring LTD Keeper on Kubernetes
####################################

In a production deployment, Keeper is configured entirely through environment variables (see :file:`config.py` in the Keeper repo).
The pod template files set these environment variables through `Kubernetes Secrets <https://kubernetes.io/docs/user-guide/secrets/>`_ and `ConfigMaps <https://kubernetes.io/docs/tasks/configure-pod-container/configmap/>`_.
See the ``env`` section in :file:`kubernetes/keeper-pod.yaml`, for example.

The Keeper Git repository includes four configuration templates:

1. :file:`kubernetes/keeper-config.template.yaml` creates a ConfigMap resource named ``keeper-config`` and is used for non-secure Keeper Flask web app configurations.
2. :file:`kubernetes/keeper-secrets.template.yaml` creates a Secret resource named ``keeper-secrets`` and is used to configure the Keeper Flask web app.
3. :file:`kubernetes/ssl-proxy-secrets.template.yaml` creates a Secret resource named ``ssl-proxy-secret`` and is used to supply TLS certs to the Nginx proxy service.
4. :file:`kubernetes/cloudsql-secrets` creates a Secret resource named ``cloudsql-secrets`` containing credentials for the Google Cloud SQL instance. 

Using the secrets
=================

The best way to maintain configurations is copy the configuration templates and modify them.
Since the staging and production environments might have different secrets, we recommend maintaining both ``-prod`` and ``-staging`` files:

.. code-block:: bash

   cp kubernetes/keeper-config.template.yaml kubernetes/keeper-config-prod.yaml
   cp kubernetes/keeper-config.template.yaml kubernetes/keeper-config-staging.yaml
   cp kubernetes/keeper-secrets.template.yaml kubernetes/keeper-secrets-prod.yaml
   cp kubernetes/keeper-secrets.template.yaml kubernetes/keeper-secrets-staging.yaml
   cp kubernetes/ssl-proxy-secrets.template.yaml kubernetes/ssl-proxy-secrets-prod.yaml
   cp kubernetes/ssl-proxy-secrets.template.yaml kubernetes/ssl-proxy-secrets-staging.yaml
   cp kubernetes/cloudsql-secrets.template.yaml kubernetes/cloudsql-secrets-prod.yaml
   cp kubernetes/cloudsql-secrets.template.yaml kubernetes/cloudsql-secrets-staging.yaml

These configuration files are automatically ignored by Git.

Setting and deploying secrets
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

keeper-config reference
=======================

The ``keeper-config`` resource (:file:`kubernetes/keeper-config.template.yaml`) provides non-secure configurations for the Flask app.

``server-name`` → ``LTD_KEEPER_URL``
   The externally-facing domain name of the Keeper API server (for example, ``keeper.lsst.codes``).
   For a Kubernetes deployment this is the domain name attached to the external IP of the Ingress resource.
   Use ``keeper-staging.lsst.codes`` for staging deployments.

``profile`` → ``LTD_KEEPER_PROFILE``
   Configuration profile for the Flask app.
   This should be ``'production'`` for any Kubernetes deployment, even a staging deployment.

``url-scheme`` → ``LTD_KEEPER_URL_SCHEME``
   Configuration profile for the Flask app.
   URL scheme for the Flask App.
   Should be ``'https'`` since the Kubernetes deployment uses a TLS-terminating ingress proxy.

``dasher-url`` → ``LTD_DASHER_URL``
   Cluster URL of the LTD Dasher app.
   This is determined by the Dasher app's service, and defaults to ``'http://dasher:3031
   Configuration profile for the Flask app.
   URL scheme for the Flask App.
   Should be ``'https'`` since the Kubernetes deployment uses a TLS-terminating ingress proxy.

keeper-secrets reference
========================

The ``keeper-secrets`` resource (:file:`kubernetes/keeper-secrets.template.yaml`) provides secure configurations for the Flask app.

``secret-key`` → ``LTD_KEEPER_SECRET_KEY``
   The secret key for authentication.

``aws-id`` → ``LTD_KEEPER_AWS_ID``
   Amazon Web Services key ID.
   This key must have access to AWS Route 53 and S3 for the documentation domains and storage bucket, respectively, used by LSST the Docs.

``aws-secret`` → ``LTD_KEEPER_AWS_SECRET``
   Amazon Web Services secret corresponding to ``LTD_KEEPER_AWS_ID``.

``fastly-id`` → ``LTD_KEEPER_FASTLY_ID``
   Fastly service ID.

``fastly-key`` → ``LTD_KEEPER_FASTLY_KEY``
   Fastly API key.

``default-user`` → ``LTD_KEEPER_BOOTSTRAP_USER``
   Username of the initial user for bootstrapping a Keeper DB.
   This bootstrap user is granted full API permissions.

``default-password`` → ``LTD_KEEPER_BOOTSTRAP_PASSWORD``
   Password for the bootstrap user.

``db-url`` → ``LTD_KEEPER_DB_URL``
   URL of Keeper's SQL database.
   For a Cloud SQL instance, this URL has the form:
   
   .. code-block:: text
   
      mysql+pymysql://root:<PASSWORD>@/keeper?unix_socket=/cloudsql/<PROJECT>:<REGION>:<INSTANCE>

   Replace ``PASSWORD`` with the database password (see :doc:`gke-cloudsql`), along with ``PROJECT`` and ``REGION`` with the Cloud SQL instance details (see :doc:`gke-setup` and doc:`gke-cloudsql``).
   Remember that this is a URI, so any unusual characters (particularly in the password) must be escaped/quoted.
   Python's `urllib.parse.quote <https://docs.python.org/3/library/urllib.parse.html#urllib.parse.quote>`__ can help prepare a URL.
   See the `SQLAlchemy Database Urls docs <http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls>`_ for more information.

   Finally, note that we recommend the ``pymysql`` 'dialect' MySQL.
   The PyMySQL package is automatically installed with LTD Keeper in its docker container.

cloudsql-secrets reference
==========================

This section describes :file:`kubernetes/cloudsql-secrets.yaml`, which provides the ``cloudsql-secrets`` resource.

``file.json``
   This is a base64-encoded JSON service account credential file.
   A Google Cloud Platform Service Account was created earlier in :doc:`gke-cloudsql`.

   .. code-block:: bash

      base64 -i credentials.json | pbcopy

Further documentation for the Cloud SQL Proxy can be found in the `github.com/GoogleCloudPlatform/cloudsql-proxy <https://github.com/GoogleCloudPlatform/cloudsql-proxy>`__ repository's README.

ssl-proxy-secret reference
==========================

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
