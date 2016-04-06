########################
Deployment on Kubernetes
########################

LSST SQuaRE uses Kubernetes on Google Container Engine to deploy LTD Keeper.
This page will guide you through the steps to deploy and maintain LTD Keeper in this environment.
It is certainly possible to deploy LTD Keeper on other platforms (whether Docker container-based on not.

Keeper API Pod Configuration
============================

Keeper is configured through the following environment variables when run in a production context.

``LTD_KEEPER_SECRET_KEY``
   The secret key for authentication.

``LTD_KEEPER_DB_URL``
   URL of Keeper's SQL database.
   For SQLite, this is in the form ``'sqlite:///path/to/db.sqlite'``.
   See the `SQLAlchemy Database Urls docs <http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls>`_ for more information.

``LTD_KEEPER_BOOTSTRAP_USER``
   Username of the initial user for bootstrapping a Keeper DB.
   This bootstrap user is granted full API permissions.

``LTD_KEEPER_BOOTSTRAP_PASSWORD``
   Password for the bootstrap user.

``LTD_KEEPER_URL``
   The externally-facing domain name of the Keeper API server (e.g., ``ltd-keeper.lsst.codes``.
   For a Kubernetes deployment this is the domain name attached to the external IP of the Ingress resource.

``LTD_KEEPER_URL_SCHEME``
   If the Ingress resource terminates TLS, this should be ``https``. Otherwise it is ``http``.

``LTD_KEEPER_AWS_ID``
   Amazon Web Services key ID. This key must have access to AWS Route 53 and S3 for the documentation domains and storage bucket, respectively, used by LSST the Docs.

``LTD_KEEPER_AWS_SECRET``
   Amazon Web Services secret corresponding to ``LTD_KEEPER_AWS_ID``.
