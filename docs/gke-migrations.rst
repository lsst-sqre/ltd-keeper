########################################################
Applying Database Migrations in Production on Kubernetes
########################################################

Unlike regular application code changes, database schema migrations in production require actual downtime.
We haven't built infrastructure to seamlessly switch between schemas in production.

Prerequisites
=============

- This procedure should only be followed for application updates that change DB schema and have an Alembic migration.
  See :doc:`dev-migrations` for information about creating migrations with Alembic.
- A new docker image with the DB change should be pushed to Docker Hub.
- Check if additional steps are needed to apply the migration, such as seeding new data into the DB.

Procedure
=========

1. Bring the deployment down:

   .. code-block:: bash

      kubectl delete keeper-deployment

   Watch for the pods to be deleted with ``kubectl get pods``.

2. Deploy the maintenance pod.

   First update :file:`keeper-mgmt-pod.yaml` with the new uWSGI container's ``image`` name.
   Look for the lines:

   .. code-block:: yaml

      - name: uwsgi
        image: "lsstsqre/ltd-keeper:latest"  # update this

   Then deploy the pod:

   .. code-block:: yaml

      kubectl create -f keeper-mgmt-pod.yaml

3. Log into the maintenance pod and apply the migration:

   .. code-block:: bash
   
      kubectl exec keeper-mgmt -c uwsgi -i -t /bin/bash

   To apply the migration:

   .. code-block:: bash

      ./run.py db upgrade
   
   When the upgrade is complete, log out of the management pod's shell:

   .. code-block:: bash

      exit

4. Delete the management pod:

   .. code-block:: bash

      kubectl delete pod keeper-mgmt

5. Deploy the application.

   First update the uWSGI container's ``image`` name in :file:`keeper-deployment.yaml` to match the one used by the maintenance pod, and deploy it:

   .. code-block:: bash

      kubectl create -f keeper-deployment
